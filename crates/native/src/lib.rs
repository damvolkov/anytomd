// ##### DEPENDENCIES #####

use std::borrow::Cow;
use std::path::Path;
use std::sync::Arc;
use std::sync::Mutex;
use std::sync::OnceLock;

use anytomd::AsyncConversionOptions;
use anytomd::AsyncImageDescriber;
use anytomd::ConversionOptions;
use anytomd::ImageDescriber;
use anytomd::WarningCode;
use anytomd::convert_bytes as rs_convert_bytes;
use anytomd::convert_bytes_async as rs_convert_bytes_async;
use anytomd::convert_file as rs_convert_file;
use anytomd::convert_file_async as rs_convert_file_async;
use anytomd::detection::detect_format as rs_detect_format;
use anytomd::detection::detect_zip_format as rs_detect_zip_format;
use anytomd::gemini::AsyncGeminiDescriber as RsAsyncGemini;
use anytomd::gemini::GeminiDescriber as RsGemini;
use pyo3::exceptions::PyException;
use pyo3::exceptions::PyOSError;
use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use pyo3::types::PyBytes;
use tokio::sync::oneshot;

type PyObj = Py<PyAny>;

const DEFAULT_MAX_INPUT_BYTES: usize = 8 * 1024 * 1024 * 1024;
const DEFAULT_MAX_TOTAL_IMAGE_BYTES: usize = 4 * 1024 * 1024 * 1024;
const DEFAULT_MAX_UNCOMPRESSED_ZIP_BYTES: usize = 16 * 1024 * 1024 * 1024;

// ##### EXCEPTIONS #####

pyo3::create_exception!(anytomd._native, ConvertError, PyException);
pyo3::create_exception!(anytomd._native, UnsupportedFormatError, ConvertError);
pyo3::create_exception!(anytomd._native, FormatNotSupportedError, ConvertError);
pyo3::create_exception!(anytomd._native, InputTooLargeError, ConvertError);
pyo3::create_exception!(anytomd._native, MalformedDocumentError, ConvertError);
pyo3::create_exception!(anytomd._native, ImageDescriptionError, ConvertError);
pyo3::create_exception!(anytomd._native, ZipError, ConvertError);
pyo3::create_exception!(anytomd._native, XmlError, ConvertError);
pyo3::create_exception!(anytomd._native, SpreadsheetError, ConvertError);
pyo3::create_exception!(anytomd._native, Utf8Error, ConvertError);

fn to_py_err(py: Python<'_>, error: anytomd::ConvertError) -> PyErr {
    use anytomd::ConvertError as E;
    let message = error.to_string();
    match error {
        E::UnsupportedFormat { .. } => UnsupportedFormatError::new_err(message),
        E::FormatNotSupported { .. } => FormatNotSupportedError::new_err(message),
        E::InputTooLarge { size, limit } => {
            let error = InputTooLargeError::new_err(message);
            let value = error.value(py);
            let _ = value.setattr("size", size);
            let _ = value.setattr("limit", limit);
            PyErr::from_value(value.clone().into_any())
        }
        E::MalformedDocument { .. } => MalformedDocumentError::new_err(message),
        E::ImageDescriptionError { .. } => ImageDescriptionError::new_err(message),
        E::ZipError(_) => ZipError::new_err(format!("failed to read ZIP archive: {message}")),
        E::XmlError(_) => XmlError::new_err(format!("failed to parse XML: {message}")),
        E::SpreadsheetError(_) => {
            SpreadsheetError::new_err(format!("failed to read spreadsheet: {message}"))
        }
        E::Utf8Error(_) => Utf8Error::new_err(format!("invalid UTF-8 content: {message}")),
        E::Io(source) => PyOSError::new_err(format!("I/O error: {source}")),
    }
}

// ##### RESULT #####

#[pyclass(module = "anytomd._native", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct ConversionResult {
    inner: anytomd::ConversionResult,
}

impl From<anytomd::ConversionResult> for ConversionResult {
    fn from(inner: anytomd::ConversionResult) -> Self {
        Self { inner }
    }
}

#[pymethods]
impl ConversionResult {
    #[getter]
    fn markdown(&self) -> String {
        self.inner.markdown.clone()
    }

    #[getter]
    fn plain_text(&self) -> String {
        self.inner.plain_text.clone()
    }

    #[getter]
    fn title(&self) -> Option<String> {
        self.inner.title.clone()
    }

    #[getter]
    fn images(&self, py: Python<'_>) -> Vec<(String, PyObj)> {
        self.inner
            .images
            .iter()
            .map(|(name, data)| {
                (
                    name.clone(),
                    PyBytes::new(py, data).as_any().clone().unbind(),
                )
            })
            .collect()
    }

    #[getter]
    fn warnings(&self) -> Vec<ConversionWarning> {
        self.inner
            .warnings
            .iter()
            .map(ConversionWarning::from)
            .collect()
    }

    fn __repr__(&self) -> String {
        format!(
            "ConversionResult(markdown={} chars, title={:?}, images={}, warnings={})",
            self.inner.markdown.len(),
            self.inner.title,
            self.inner.images.len(),
            self.inner.warnings.len(),
        )
    }
}

#[pyclass(module = "anytomd._native", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct ConversionWarning {
    code: String,
    message: String,
    location: Option<String>,
}

impl From<&anytomd::ConversionWarning> for ConversionWarning {
    fn from(warning: &anytomd::ConversionWarning) -> Self {
        let code = match warning.code {
            WarningCode::SkippedElement => "skipped_element",
            WarningCode::UnsupportedFeature => "unsupported_feature",
            WarningCode::ResourceLimitReached => "resource_limit_reached",
            WarningCode::MalformedSegment => "malformed_segment",
        };
        Self {
            code: code.to_string(),
            message: warning.message.clone(),
            location: warning.location.clone(),
        }
    }
}

#[pymethods]
impl ConversionWarning {
    #[getter]
    fn code(&self) -> String {
        self.code.clone()
    }

    #[getter]
    fn message(&self) -> String {
        self.message.clone()
    }

    #[getter]
    fn location(&self) -> Option<String> {
        self.location.clone()
    }

    fn __repr__(&self) -> String {
        format!(
            "ConversionWarning(code={:?}, message={:?}, location={:?})",
            self.code, self.message, self.location
        )
    }
}

// ##### DESCRIBERS #####

struct PythonDescriber(PyObj);

impl ImageDescriber for PythonDescriber {
    fn describe(
        &self,
        image_bytes: &[u8],
        mime_type: &str,
        prompt: &str,
    ) -> Result<String, anytomd::ConvertError> {
        let outcome = Python::attach(|py| {
            let args = (PyBytes::new(py, image_bytes), mime_type, prompt);
            self.0
                .call1(py, args)
                .and_then(|value| value.extract::<String>(py))
        });
        outcome.map_err(|error| anytomd::ConvertError::ImageDescriptionError {
            reason: error.to_string(),
        })
    }
}

struct PythonAsyncDescriber {
    callable: PyObj,
    loop_: PyObj,
}

impl AsyncImageDescriber for PythonAsyncDescriber {
    fn describe<'a>(
        &'a self,
        image_bytes: &'a [u8],
        mime_type: &'a str,
        prompt: &'a str,
    ) -> anytomd::converter::AsyncDescribeFuture<'a> {
        Box::pin(async move {
            let receiver = Python::attach(|py| {
                let coroutine = self
                    .callable
                    .call1(py, (PyBytes::new(py, image_bytes), mime_type, prompt))?;
                let future = py.import("asyncio")?.call_method1(
                    "run_coroutine_threadsafe",
                    (coroutine.bind(py), self.loop_.bind(py)),
                )?;
                let (sender, receiver) = oneshot::channel::<Result<String, String>>();
                let callback = Py::new(
                    py,
                    DoneCallback {
                        sender: Mutex::new(Some(sender)),
                    },
                )?;
                future.call_method1("add_done_callback", (callback,))?;
                Ok::<_, PyErr>(receiver)
            })
            .map_err(|error| anytomd::ConvertError::ImageDescriptionError {
                reason: error.to_string(),
            })?;

            receiver
                .await
                .map_err(|_| anytomd::ConvertError::ImageDescriptionError {
                    reason: "description channel closed".to_string(),
                })?
                .map_err(|reason| anytomd::ConvertError::ImageDescriptionError { reason })
        })
    }
}

#[pyclass(module = "anytomd._native")]
struct DoneCallback {
    sender: Mutex<Option<oneshot::Sender<Result<String, String>>>>,
}

#[pymethods]
impl DoneCallback {
    fn __call__(&self, future: &Bound<'_, PyAny>) {
        let Some(sender) = self.sender.lock().ok().and_then(|mut slot| slot.take()) else {
            return;
        };
        let outcome = match future.call_method0("result") {
            Ok(value) => value.extract::<String>().map_err(|error| error.to_string()),
            Err(error) => Err(error.to_string()),
        };
        let _ = sender.send(outcome);
    }
}

fn describer_for(value: &Bound<'_, PyAny>) -> Arc<dyn ImageDescriber> {
    match value.extract::<GeminiDescriber>() {
        Ok(gemini) => gemini.inner,
        Err(_) => Arc::new(PythonDescriber(value.clone().unbind())),
    }
}

fn async_describer_for(value: &Bound<'_, PyAny>, loop_: PyObj) -> Arc<dyn AsyncImageDescriber> {
    match value.extract::<AsyncGeminiDescriber>() {
        Ok(gemini) => gemini.inner,
        Err(_) => Arc::new(PythonAsyncDescriber {
            callable: value.clone().unbind(),
            loop_,
        }),
    }
}

#[pyclass(module = "anytomd._native", frozen, from_py_object)]
#[derive(Clone)]
struct GeminiDescriber {
    inner: Arc<dyn ImageDescriber>,
}

#[pymethods]
impl GeminiDescriber {
    #[new]
    #[pyo3(signature = (api_key = None, model = None))]
    fn new(api_key: Option<String>, model: Option<String>) -> PyResult<Self> {
        let describer = match api_key {
            Some(key) => RsGemini::new(key),
            None => RsGemini::from_env()
                .map_err(|error| ImageDescriptionError::new_err(error.to_string()))?,
        };
        let describer = match model {
            Some(name) => describer.with_model(name),
            None => describer,
        };
        Ok(Self {
            inner: Arc::new(describer),
        })
    }

    fn __call__(
        &self,
        py: Python<'_>,
        image: &Bound<'_, PyBytes>,
        mime_type: &str,
        prompt: &str,
    ) -> PyResult<String> {
        let inner = self.inner.clone();
        let image = image.as_bytes().to_vec();
        let mime_type = mime_type.to_string();
        let prompt = prompt.to_string();
        let outcome = py.detach(move || {
            inner
                .describe(&image, &mime_type, &prompt)
                .map_err(|error| error.to_string())
        });
        outcome.map_err(ImageDescriptionError::new_err)
    }
}

#[pyclass(module = "anytomd._native", frozen, from_py_object)]
#[derive(Clone)]
struct AsyncGeminiDescriber {
    inner: Arc<dyn AsyncImageDescriber>,
}

#[pymethods]
impl AsyncGeminiDescriber {
    #[new]
    #[pyo3(signature = (api_key = None, model = None))]
    fn new(api_key: Option<String>, model: Option<String>) -> PyResult<Self> {
        let describer = match api_key {
            Some(key) => RsAsyncGemini::new(key),
            None => RsAsyncGemini::from_env()
                .map_err(|error| ImageDescriptionError::new_err(error.to_string()))?,
        };
        let describer = match model {
            Some(name) => describer.with_model(name),
            None => describer,
        };
        Ok(Self {
            inner: Arc::new(describer),
        })
    }
}

// ##### OPTIONS #####

#[allow(clippy::too_many_arguments)]
fn base_options(
    extract_images: bool,
    extract_comments: bool,
    strict: bool,
    max_input_bytes: usize,
    max_total_image_bytes: usize,
    max_uncompressed_zip_bytes: usize,
    image_describer: Option<&Bound<'_, PyAny>>,
) -> ConversionOptions {
    ConversionOptions {
        extract_images,
        extract_comments,
        strict,
        max_input_bytes,
        max_total_image_bytes,
        max_uncompressed_zip_bytes,
        image_describer: image_describer.map(describer_for),
    }
}

#[allow(clippy::too_many_arguments)]
fn async_options(
    extract_images: bool,
    extract_comments: bool,
    strict: bool,
    max_input_bytes: usize,
    max_total_image_bytes: usize,
    max_uncompressed_zip_bytes: usize,
    async_image_describer: Option<Bound<'_, PyAny>>,
    loop_: Option<PyObj>,
) -> AsyncConversionOptions {
    AsyncConversionOptions {
        base: base_options(
            extract_images,
            extract_comments,
            strict,
            max_input_bytes,
            max_total_image_bytes,
            max_uncompressed_zip_bytes,
            None,
        ),
        async_image_describer: async_image_describer.as_ref().map(|value| {
            async_describer_for(value, loop_.expect("loop captured with async describer"))
        }),
    }
}

fn path_of<'py>(py: Python<'py>, path: &Bound<'py, PyAny>) -> PyResult<String> {
    let resolved = py.import("os")?.call_method1("fspath", (path,))?;
    Ok(resolved.extract::<Cow<'_, str>>()?.into_owned())
}

fn running_loop(py: Python<'_>) -> PyResult<PyObj> {
    py.import("asyncio")?
        .call_method0("get_running_loop")
        .map(Bound::unbind)
}

// ##### RUNTIME #####

fn runtime() -> &'static tokio::runtime::Runtime {
    static RUNTIME: OnceLock<tokio::runtime::Runtime> = OnceLock::new();
    RUNTIME.get_or_init(|| {
        tokio::runtime::Builder::new_multi_thread()
            .worker_threads(4)
            .thread_name("anytomd")
            .enable_all()
            .build()
            .expect("anytomd runtime")
    })
}

// ##### CONVERSION #####

#[pyfunction]
#[allow(clippy::too_many_arguments)]
#[pyo3(
    signature = (path, *, extract_images = false, extract_comments = false, strict = false,
                 max_input_bytes = DEFAULT_MAX_INPUT_BYTES,
                 max_total_image_bytes = DEFAULT_MAX_TOTAL_IMAGE_BYTES,
                 max_uncompressed_zip_bytes = DEFAULT_MAX_UNCOMPRESSED_ZIP_BYTES,
                 image_describer = None)
)]
fn convert_file(
    py: Python<'_>,
    path: &Bound<'_, PyAny>,
    extract_images: bool,
    extract_comments: bool,
    strict: bool,
    max_input_bytes: usize,
    max_total_image_bytes: usize,
    max_uncompressed_zip_bytes: usize,
    image_describer: Option<Bound<'_, PyAny>>,
) -> PyResult<ConversionResult> {
    let path = path_of(py, path)?;
    std::fs::metadata(&path).map_err(|error| PyOSError::new_err(format!("{path}: {error}")))?;
    let options = base_options(
        extract_images,
        extract_comments,
        strict,
        max_input_bytes,
        max_total_image_bytes,
        max_uncompressed_zip_bytes,
        image_describer.as_ref(),
    );
    let outcome =
        py.detach(move || rs_convert_file(Path::new(&path), &options).map(ConversionResult::from));
    outcome.map_err(|error| to_py_err(py, error))
}

#[pyfunction]
#[allow(clippy::too_many_arguments)]
#[pyo3(
    signature = (data, format, *, extract_images = false, extract_comments = false, strict = false,
                 max_input_bytes = DEFAULT_MAX_INPUT_BYTES,
                 max_total_image_bytes = DEFAULT_MAX_TOTAL_IMAGE_BYTES,
                 max_uncompressed_zip_bytes = DEFAULT_MAX_UNCOMPRESSED_ZIP_BYTES,
                 image_describer = None)
)]
fn convert_bytes(
    py: Python<'_>,
    data: &Bound<'_, PyBytes>,
    format: String,
    extract_images: bool,
    extract_comments: bool,
    strict: bool,
    max_input_bytes: usize,
    max_total_image_bytes: usize,
    max_uncompressed_zip_bytes: usize,
    image_describer: Option<Bound<'_, PyAny>>,
) -> PyResult<ConversionResult> {
    let options = base_options(
        extract_images,
        extract_comments,
        strict,
        max_input_bytes,
        max_total_image_bytes,
        max_uncompressed_zip_bytes,
        image_describer.as_ref(),
    );
    let bytes = data.as_bytes().to_vec();
    let outcome =
        py.detach(move || rs_convert_bytes(&bytes, &format, &options).map(ConversionResult::from));
    outcome.map_err(|error| to_py_err(py, error))
}

#[pyfunction]
#[allow(clippy::too_many_arguments)]
#[pyo3(
    signature = (path, *, extract_images = false, extract_comments = false, strict = false,
                 max_input_bytes = DEFAULT_MAX_INPUT_BYTES,
                 max_total_image_bytes = DEFAULT_MAX_TOTAL_IMAGE_BYTES,
                 max_uncompressed_zip_bytes = DEFAULT_MAX_UNCOMPRESSED_ZIP_BYTES,
                 async_image_describer = None)
)]
async fn convert_file_async(
    path: Py<PyAny>,
    extract_images: bool,
    extract_comments: bool,
    strict: bool,
    max_input_bytes: usize,
    max_total_image_bytes: usize,
    max_uncompressed_zip_bytes: usize,
    async_image_describer: Option<Py<PyAny>>,
) -> PyResult<ConversionResult> {
    let (path, options) = Python::attach(|py| -> PyResult<(String, AsyncConversionOptions)> {
        let path = path_of(py, path.bind(py))?;
        std::fs::metadata(&path).map_err(|error| PyOSError::new_err(format!("{path}: {error}")))?;
        let loop_ = async_image_describer
            .as_ref()
            .map(|_| running_loop(py))
            .transpose()?;
        let describer = async_image_describer
            .as_ref()
            .map(|describer| describer.bind(py).clone());
        let options = async_options(
            extract_images,
            extract_comments,
            strict,
            max_input_bytes,
            max_total_image_bytes,
            max_uncompressed_zip_bytes,
            describer,
            loop_,
        );
        Ok((path, options))
    })?;
    let handle =
        runtime().spawn(async move { rs_convert_file_async(Path::new(&path), &options).await });
    let outcome = handle
        .await
        .map_err(|error| PyRuntimeError::new_err(format!("conversion panicked: {error}")))?
        .map(ConversionResult::from);
    Python::attach(|py| outcome.map_err(|error| to_py_err(py, error)))
}

#[pyfunction]
#[allow(clippy::too_many_arguments)]
#[pyo3(
    signature = (data, format, *, extract_images = false, extract_comments = false, strict = false,
                 max_input_bytes = DEFAULT_MAX_INPUT_BYTES,
                 max_total_image_bytes = DEFAULT_MAX_TOTAL_IMAGE_BYTES,
                 max_uncompressed_zip_bytes = DEFAULT_MAX_UNCOMPRESSED_ZIP_BYTES,
                 async_image_describer = None)
)]
async fn convert_bytes_async(
    data: Py<PyBytes>,
    format: String,
    extract_images: bool,
    extract_comments: bool,
    strict: bool,
    max_input_bytes: usize,
    max_total_image_bytes: usize,
    max_uncompressed_zip_bytes: usize,
    async_image_describer: Option<Py<PyAny>>,
) -> PyResult<ConversionResult> {
    let (bytes, options) = Python::attach(|py| -> PyResult<(Vec<u8>, AsyncConversionOptions)> {
        let loop_ = async_image_describer
            .as_ref()
            .map(|_| running_loop(py))
            .transpose()?;
        let describer = async_image_describer
            .as_ref()
            .map(|describer| describer.bind(py).clone());
        let options = async_options(
            extract_images,
            extract_comments,
            strict,
            max_input_bytes,
            max_total_image_bytes,
            max_uncompressed_zip_bytes,
            describer,
            loop_,
        );
        Ok((data.bind(py).as_bytes().to_vec(), options))
    })?;
    let handle =
        runtime().spawn(async move { rs_convert_bytes_async(&bytes, &format, &options).await });
    let outcome = handle
        .await
        .map_err(|error| PyRuntimeError::new_err(format!("conversion panicked: {error}")))?
        .map(ConversionResult::from);
    Python::attach(|py| outcome.map_err(|error| to_py_err(py, error)))
}

#[pyfunction]
fn detect_format(
    py: Python<'_>,
    path: &Bound<'_, PyAny>,
    data: &Bound<'_, PyBytes>,
) -> PyResult<Option<String>> {
    let path = path_of(py, path)?;
    Ok(rs_detect_format(Path::new(&path), data.as_bytes()).map(str::to_string))
}

#[pyfunction]
fn detect_zip_format(data: &Bound<'_, PyBytes>) -> Option<String> {
    rs_detect_zip_format(data.as_bytes()).map(str::to_string)
}

// ##### MODULE #####

#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    let py = m.py();
    m.add_function(wrap_pyfunction!(convert_file, m)?)?;
    m.add_function(wrap_pyfunction!(convert_bytes, m)?)?;
    m.add_function(wrap_pyfunction!(convert_file_async, m)?)?;
    m.add_function(wrap_pyfunction!(convert_bytes_async, m)?)?;
    m.add_function(wrap_pyfunction!(detect_format, m)?)?;
    m.add_function(wrap_pyfunction!(detect_zip_format, m)?)?;
    m.add_class::<ConversionResult>()?;
    m.add_class::<ConversionWarning>()?;
    m.add_class::<GeminiDescriber>()?;
    m.add_class::<AsyncGeminiDescriber>()?;
    for (name, class) in [
        ("ConvertError", py.get_type::<ConvertError>()),
        (
            "UnsupportedFormatError",
            py.get_type::<UnsupportedFormatError>(),
        ),
        (
            "FormatNotSupportedError",
            py.get_type::<FormatNotSupportedError>(),
        ),
        ("InputTooLargeError", py.get_type::<InputTooLargeError>()),
        (
            "MalformedDocumentError",
            py.get_type::<MalformedDocumentError>(),
        ),
        (
            "ImageDescriptionError",
            py.get_type::<ImageDescriptionError>(),
        ),
        ("ZipError", py.get_type::<ZipError>()),
        ("XmlError", py.get_type::<XmlError>()),
        ("SpreadsheetError", py.get_type::<SpreadsheetError>()),
        ("Utf8Error", py.get_type::<Utf8Error>()),
    ] {
        m.add(name, class)?;
    }
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}
