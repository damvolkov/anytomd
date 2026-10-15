# Async

`convert_file_async` and `convert_bytes_async` are native coroutines: the same conversions, awaitable from any asyncio code.

```python
import asyncio
from anytomd import convert_bytes_async

async def main() -> None:
    result = await convert_bytes_async(b"Name,Age\nAlice,30\n", "csv")
    print(result.markdown)

asyncio.run(main())
```

## What runs where

| Work | Where it runs |
|---|---|
| Parsing and rendering | An internal Rust thread pool (one worker per core), never the event loop |
| `async def` describers | Your running event loop, all images of a document concurrently |
| `AsyncGeminiDescriber` | The Rust thread pool, concurrent native HTTP |
| Result construction | The event loop thread, once, at the end |

The loop stays free while a document converts: other tasks keep running.

## Many documents at once

```python
import asyncio
from pathlib import Path
from anytomd import convert_file_async

async def convert_folder(folder: Path, limit: int = 8) -> dict[str, str]:
    gate = asyncio.Semaphore(limit)

    async def one(path: Path) -> tuple[str, str]:
        async with gate:
            return path.name, (await convert_file_async(path)).markdown

    async with asyncio.TaskGroup() as group:
        tasks = [group.create_task(one(path)) for path in folder.glob("*.docx")]
    return dict(task.result() for task in tasks)
```

Bound the fan-out: each in-flight conversion holds its document in memory.

## Cancellation

Cancelling the awaiting task cancels the conversion: the Rust task is aborted at its next suspension point and every in-flight `async def` describer receives `CancelledError`.

```python
task = asyncio.create_task(convert_file_async("deck.pptx", async_image_describer=describe))
task.cancel()   # describers awaiting the provider are cancelled too
```

Parsing itself is CPU work with no suspension points; a document already being parsed finishes parsing in the background, then is dropped.

## Sync or async?

| You have | Use |
|---|---|
| A script, a CLI, a worker thread | `convert_file` / `convert_bytes` |
| A thread pool of conversions | `convert_file` — it releases the GIL, threads run in parallel |
| An asyncio service (FastAPI, aiohttp, …) | `convert_file_async` / `convert_bytes_async` |
| Documents with many images and an LLM describer | The async variants — descriptions run concurrently |

## Options are the same

Every keyword of the sync functions exists on the async ones, except that `image_describer` becomes `async_image_describer`. → [Options](../reference/options.md)
