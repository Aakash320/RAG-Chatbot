/**
 * Minimal SSE (Server-Sent Events) reader for fetch() streaming responses.
 *
 * The backend sends blocks separated by a blank line, shaped like:
 *   event: token
 *   data: {"text": "Hello"}
 *
 * `onEvent(eventName, data)` fires once per parsed block, with `data`
 * already JSON.parsed.
 */
export async function readSSEStream(response, onEvent) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop(); // last (possibly incomplete) block stays buffered

    for (const block of blocks) {
      if (!block.trim()) continue;

      let eventName = "message";
      let dataLine = "";

      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) eventName = line.slice(6).trim();
        else if (line.startsWith("data:")) dataLine += line.slice(5).trim();
      }

      if (!dataLine) continue;

      try {
        onEvent(eventName, JSON.parse(dataLine));
      } catch {
        // Ignore a malformed chunk rather than crashing the reader loop.
      }
    }
  }
}