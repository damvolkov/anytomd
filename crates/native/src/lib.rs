// ##### DEPENDENCIES #####

use std::any::Any;
use std::future::Future;
use std::panic::AssertUnwindSafe;
use std::path::Path;
use std::path::PathBuf;
use std::pin::Pin;
use std::sync::Arc;
use std::sync::Mutex;
use std::sync::OnceLock;
use std::task::Context;
use std::task::Poll;

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
use pyo3::exceptions::PyTypeError;
use pyo3::prelude::*;
use pyo3::pybacked::PyBackedBytes;
use pyo3::types::PyBytes;
use pyo3::types::PyString;
use tokio::sync::oneshot;
use tokio::task::JoinError;
use tokio::task::JoinHandle;

type PyObj = Py<PyAny>;
type Outcome = Result<anytomd::ConversionResult, anytomd::ConvertError>;

const DEFAULT_MAX_INPUT_BYTES: usize = 8 * 1024 * 1024 * 1024;
const DEFAULT_MAX_TOTAL_IMAGE_BYTES: usize = 4 * 1024 * 1024 * 1024;
const DEFAULT_MAX_UNCOMPRESSED_ZIP_BYTES: usize = 16 * 1024 * 1024 * 1024;

// ##### EXCEPTIONS #####

pyo3::create_exception!(
    anytomd._native,
    ConvertError,
    PyException,
    "Base of every conversion failure."
);
pyo3::create_exception!(
    anytomd._native,
    UnsupportedFormatError,
    ConvertError,
    "No converter recognizes the format."
);
pyo3::create_exception!(
    anytomd._native,
    FormatNotSupportedError,
    ConvertError,
    "Format recognized but intentionally refused (PDF)."
);
pyo3::create_exception!(
    anytomd._native,
    InputTooLargeError,
    ConvertError,
    "Input or decompressed archive exceeds its limit; carries `size` and `limit`."
);
pyo3::create_exception!(
    anytomd._native,
    MalformedDocumentError,
    ConvertError,
    "Document structure broken beyond recovery, or a warning under `strict=True`."
);
pyo3::create_exception!(
    anytomd._native,
    ImageDescriptionError,
    ConvertError,
    "An image describer could not be built or failed."
);
pyo3::create_exception!(
    anytomd._native,
    ZipError,
    ConvertError,
    "ZIP container (DOCX, PPTX, XLSX) unreadable."
);
pyo3::create_exception!(
    anytomd._native,
    XmlError,
    ConvertError,
    "XML inside the document unparseable."
);
pyo3::create_exception!(
    anytomd._native,
    SpreadsheetError,
    ConvertError,
    "Workbook (XLSX, XLS) unreadable."
);
pyo3::create_exception!(
    anytomd._native,
    Utf8Error,
    ConvertError,
    "Content is not valid UTF-8."
);

fn to_py_err(py: Python<'_>, error: anytomd::ConvertError, path: Option<&Path>) -> PyErr {
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
        E::ZipError(source) => ZipError::new_err(format!("{message}: {source}")),
        E::XmlError(source) => XmlError::new_err(format!("{message}: {source}")),
        E::SpreadsheetError(source) => SpreadsheetError::new_err(format!("{message}: {source}")),
        E::Utf8Error(source) => Utf8Error::new_err(format!("{message}: {source}")),
        E::Io(source) => os_error(py, source, path),
    }
}

fn os_error(py: Python<'_>, error: std::io::Error, path: Option<&Path>) -> PyErr {
    let (Some(code), Some(path)) = (error.raw_os_error(), path) else {
        return PyErr::from(error);
    };
    os_error_from(py, code, path.to_string_lossy().into_owned())
}

#[cfg(not(windows))]
fn os_error_from(py: Python<'_>, code: i32, filename: String) -> PyErr {
    py.import("os")
        .and_then(|os| os.call_method1("strerror", (code,)))
        .map_or_else(
            |failure| failure,
            |strerror| PyOSError::new_err((code, strerror.unbind(), filename)),
        )
}

// Win32 codes go in `winerror`; Python derives errno and the OSError subclass from it.
#[cfg(windows)]
fn os_error_from(_py: Python<'_>, code: i32, filename: String) -> PyErr {
    let strerror = std::io::Error::from_raw_os_error(code).to_string();
    PyOSError::new_err((0, strerror, filename, code))
}

fn panicked(reason: &str) -> PyErr {
    PyRuntimeError::new_err(format!("conversion panicked: {reason}"))
}

fn panic_reason(payload: &(dyn Any + Send)) -> &str {
    payload
        .downcast_ref::<&str>()
        .copied()
        .or_else(|| payload.downcast_ref::<String>().map(String::as_str))
        .unwrap_or("unknown panic")
}

fn join_reason(error: JoinError) -> PyErr {
    panicked(&error.to_string())
}

// ##### RESULT #####

/// Outcome of one conversion: Markdown, plain text, title, extracted images and warnings.
#[pyclass(module = "anytomd._native", frozen, skip_from_py_object)]
pub struct ConversionResult {
    markdown: Py<PyString>,
    plain_text: Py<PyString>,
    title: Option<Py<PyString>>,
    images: Vec<(Py<PyString>, Py<PyBytes>)>,
    warnings: Vec<Py<ConversionWarning>>,
}

impl ConversionResult {
    fn build(py: Python<'_>, inner: anytomd::ConversionResult) -> PyResult<Self> {
        Ok(Self {
            markdown: PyString::new(py, &inner.markdown).unbind(),
            plain_text: PyString::new(py, &inner.plain_text).unbind(),
            title: inner.title.map(|title| PyString::new(py, &title).unbind()),
            images: inner
                .images
                .iter()
                .map(|(name, data)| {
                    (
                        PyString::new(py, name).unbind(),
                        PyBytes::new(py, data).unbind(),
                    )
                })
                .collect(),
            warnings: inner
                .warnings
                .iter()
                .map(|warning| Py::new(py, ConversionWarning::from(warning)))
                .collect::<PyResult<_>>()?,
        })
    }
}

#[pymethods]
impl ConversionResult {
    /// Converted Markdown.
    #[getter]
    fn markdown(&self, py: Python<'_>) -> Py<PyString> {
        self.markdown.clone_ref(py)
    }

    /// Same content without Markdown syntax, extracted directly from the source.
    #[getter]
    fn plain_text(&self, py: Python<'_>) -> Py<PyString> {
        self.plain_text.clone_ref(py)
    }

    /// Document title (first heading or HTML `<title>`), or None.
    #[getter]
    fn title(&self, py: Python<'_>) -> Option<Py<PyString>> {
        self.title.as_ref().map(|title| title.clone_ref(py))
    }

    /// Embedded images as `(filename, bytes)`; empty unless `extract_images=True`.
    #[getter]
    fn images(&self, py: Python<'_>) -> Vec<(Py<PyString>, Py<PyBytes>)> {
        self.images
            .iter()
            .map(|(name, data)| (name.clone_ref(py), data.clone_ref(py)))
            .collect()
    }

    /// Recoverable problems met during a best-effort conversion.
    #[getter]
    fn warnings(&self, py: Python<'_>) -> Vec<Py<ConversionWarning>> {
        self.warnings
            .iter()
            .map(|warning| warning.clone_ref(py))
            .collect()
    }

    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
        let title = match &self.title {
            Some(title) => title.bind(py).repr()?.to_string(),
            None => "None".to_string(),
        };
        Ok(format!(
            "ConversionResult(markdown={} chars, title={title}, images={}, warnings={})",
            self.markdown.bind(py).len()?,
            self.images.len(),
            self.warnings.len(),
        ))
    }
}

/// A recoverable problem: `code`, human `message` and optional `location`.
#[pyclass(module = "anytomd._native", frozen, get_all, skip_from_py_object)]
pub struct ConversionWarning {
    /// One of `skipped_element`, `unsupported_feature`, `resource_limit_reached`, `malformed_segment`.
    code: &'static str,
    /// Human-readable explanation.
    message: String,
    /// Where it happened (image name, sheet, slide…), when known.
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
            code,
            message: warning.message.clone(),
            location: warning.location.clone(),
        }
    }
}

#[pymethods]
impl ConversionWarning {
    fn __repr__(&self) -> String {
        let location = self
            .location
            .as_deref()
            .map_or_else(|| "None".to_string(), |location| format!("{location:?}"));
        format!(
            "ConversionWarning(code={:?}, message={:?}, location={location})",
            self.code, self.message
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

/// Python-side future of one description; cancelled if dropped before it settles.
struct PendingCall(Option<PyObj>);

impl PendingCall {
    fn settle(mut self) {
        self.0 = None;
    }
}

impl Drop for PendingCall {
    fn drop(&mut self) {
        if let Some(future) = self.0.take() {
            Python::try_attach(|py| {
                let _ = future.call_method0(py, "cancel");
            });
        }
    }
}

impl AsyncImageDescriber for PythonAsyncDescriber {
    fn describe<'a>(
        &'a self,
        image_bytes: &'a [u8],
        mime_type: &'a str,
        prompt: &'a str,
    ) -> anytomd::converter::AsyncDescribeFuture<'a> {
        Box::pin(async move {
            let (pending, receiver) = Python::attach(|py| {
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
                Ok::<_, PyErr>((PendingCall(Some(future.unbind())), receiver))
            })
            .map_err(|error| anytomd::ConvertError::ImageDescriptionError {
                reason: error.to_string(),
            })?;

            let outcome = receiver.await;
            pending.settle();
            outcome
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

fn not_callable(value: &Bound<'_, PyAny>) -> PyErr {
    PyTypeError::new_err(format!(
        "image describer must be callable, got {}",
        value.get_type()
    ))
}

fn describer_for(value: &Bound<'_, PyAny>) -> PyResult<Arc<dyn ImageDescriber>> {
    match value.extract::<GeminiDescriber>() {
        Ok(gemini) => Ok(gemini.inner),
        Err(_) if value.is_callable() => Ok(Arc::new(PythonDescriber(value.clone().unbind()))),
        Err(_) => Err(not_callable(value)),
    }
}

fn async_describer_for(
    py: Python<'_>,
    value: &Bound<'_, PyAny>,
) -> PyResult<Arc<dyn AsyncImageDescriber>> {
    match value.extract::<AsyncGeminiDescriber>() {
        Ok(gemini) => Ok(gemini.inner),
        Err(_) if value.is_callable() => Ok(Arc::new(PythonAsyncDescriber {
            callable: value.clone().unbind(),
            loop_: running_loop(py)?,
        })),
        Err(_) => Err(not_callable(value)),
    }
}

/// Image describer backed by Google Gemini (blocking HTTP); key from `api_key` or `GEMINI_API_KEY`.
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

    /// Description of one image, computed with the GIL released.
    fn __call__(
        &self,
        py: Python<'_>,
        image: PyBackedBytes,
        mime_type: &str,
        prompt: &str,
    ) -> PyResult<String> {
        let inner = self.inner.clone();
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

/// Image describer backed by Google Gemini (async HTTP, concurrent per document); key from `api_key` or `GEMINI_API_KEY`.
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
) -> PyResult<ConversionOptions> {
    Ok(ConversionOptions {
        extract_images,
        extract_comments,
        strict,
        max_input_bytes,
        max_total_image_bytes,
        max_uncompressed_zip_bytes,
        image_describer: image_describer.map(describer_for).transpose()?,
    })
}

#[allow(clippy::too_many_arguments)]
fn async_options(
    py: Python<'_>,
    extract_images: bool,
    extract_comments: bool,
    strict: bool,
    max_input_bytes: usize,
    max_total_image_bytes: usize,
    max_uncompressed_zip_bytes: usize,
    async_image_describer: Option<&Py<PyAny>>,
) -> PyResult<AsyncConversionOptions> {
    let describer = async_image_describer
        .map(|value| async_describer_for(py, value.bind(py)))
        .transpose()?;
    // The crate only collects image bytes for an async describer when extraction is on.
    let collect = extract_images || describer.is_some();
    Ok(AsyncConversionOptions {
        base: base_options(
            collect,
            extract_comments,
            strict,
            max_input_bytes,
            max_total_image_bytes,
            max_uncompressed_zip_bytes,
            None,
        )?,
        async_image_describer: describer,
    })
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
            .thread_name("anytomd")
            .enable_all()
            .build()
            .expect("anytomd runtime")
    })
}

/// Tokio task aborted when the awaiting Python coroutine is dropped or cancelled.
struct TaskGuard<T>(JoinHandle<T>);

impl<T> Future for TaskGuard<T> {
    type Output = Result<T, JoinError>;

    fn poll(mut self: Pin<&mut Self>, context: &mut Context<'_>) -> Poll<Self::Output> {
        Pin::new(&mut self.0).poll(context)
    }
}

impl<T> Drop for TaskGuard<T> {
    fn drop(&mut self) {
        self.0.abort();
    }
}

fn run_blocking(py: Python<'_>, work: impl FnOnce() -> Outcome + Send) -> PyResult<Outcome> {
    py.detach(move || std::panic::catch_unwind(AssertUnwindSafe(work)))
        .map_err(|payload| panicked(panic_reason(payload.as_ref())))
}

fn finish(
    py: Python<'_>,
    outcome: Outcome,
    keep_images: bool,
    path: Option<&Path>,
) -> PyResult<ConversionResult> {
    let mut result = outcome.map_err(|error| to_py_err(py, error, path))?;
    if !keep_images {
        result.images.clear();
    }
    ConversionResult::build(py, result)
}

// ##### CONVERSION #####

/// Convert the document at `path` to Markdown; the format is detected from magic bytes and extension.
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
    path: PathBuf,
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
    )?;
    let outcome = run_blocking(py, || rs_convert_file(&path, &options))?;
    finish(py, outcome, extract_images, Some(&path))
}

/// Convert in-memory `data` to Markdown; `format` is an extension such as `"docx"` or `".csv"`.
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
    data: PyBackedBytes,
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
    )?;
    let outcome = run_blocking(py, || rs_convert_bytes(&data, &format, &options))?;
    finish(py, outcome, extract_images, None)
}

/// Awaitable `convert_file`: conversion runs off the event loop, image descriptions resolve concurrently.
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
    path: PathBuf,
    extract_images: bool,
    extract_comments: bool,
    strict: bool,
    max_input_bytes: usize,
    max_total_image_bytes: usize,
    max_uncompressed_zip_bytes: usize,
    async_image_describer: Option<Py<PyAny>>,
) -> PyResult<ConversionResult> {
    let options = Python::attach(|py| {
        async_options(
            py,
            extract_images,
            extract_comments,
            strict,
            max_input_bytes,
            max_total_image_bytes,
            max_uncompressed_zip_bytes,
            async_image_describer.as_ref(),
        )
    })?;
    let target = path.clone();
    let outcome =
        TaskGuard(runtime().spawn(async move { rs_convert_file_async(&target, &options).await }))
            .await
            .map_err(join_reason)?;
    Python::attach(|py| finish(py, outcome, extract_images, Some(&path)))
}

/// Awaitable `convert_bytes`: conversion runs off the event loop, image descriptions resolve concurrently.
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
    data: PyBackedBytes,
    format: String,
    extract_images: bool,
    extract_comments: bool,
    strict: bool,
    max_input_bytes: usize,
    max_total_image_bytes: usize,
    max_uncompressed_zip_bytes: usize,
    async_image_describer: Option<Py<PyAny>>,
) -> PyResult<ConversionResult> {
    let options = Python::attach(|py| {
        async_options(
            py,
            extract_images,
            extract_comments,
            strict,
            max_input_bytes,
            max_total_image_bytes,
            max_uncompressed_zip_bytes,
            async_image_describer.as_ref(),
        )
    })?;
    let outcome = TaskGuard(
        runtime().spawn(async move { rs_convert_bytes_async(&data, &format, &options).await }),
    )
    .await
    .map_err(join_reason)?;
    Python::attach(|py| finish(py, outcome, extract_images, None))
}

/// Format the engine would pick for `path` and its leading `data`, or None.
#[pyfunction]
fn detect_format(path: PathBuf, data: PyBackedBytes) -> Option<String> {
    rs_detect_format(&path, &data).map(str::to_string)
}

/// Concrete OOXML type behind ZIP magic: `"docx"`, `"pptx"`, `"xlsx"`, or None.
#[pyfunction]
fn detect_zip_format(data: PyBackedBytes) -> Option<String> {
    rs_detect_zip_format(&data).map(str::to_string)
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
