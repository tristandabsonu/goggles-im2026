async function readError(response) {
  try {
    const body = await response.json();
    return typeof body.detail === "string"
      ? body.detail
      : "The check could not be completed.";
  } catch {
    return "The check could not be completed.";
  }
}

export async function fetchDemoFile(key) {
  const response = await fetch(`/api/demo/files/${key}`);
  if (!response.ok) throw new Error(await readError(response));
  const blob = await response.blob();
  const disposition = response.headers.get("content-disposition") || "";
  const match = disposition.match(/filename="?([^";]+)"?/i);
  return new File([blob], match?.[1] || `${key}.pdf`, {
    type: "application/pdf",
  });
}

async function postProgressForm(path, formData, onProgress) {
  const response = await fetch(path, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) throw new Error(await readError(response));
  if (!response.body) throw new Error("Live check progress is unavailable in this browser.");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result = null;

  function handleEvent(block) {
    const payload = block
      .split("\n")
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trimStart())
      .join("\n");
    if (!payload) return;
    let event;
    try {
      event = JSON.parse(payload);
    } catch {
      throw new Error("The check returned an unreadable progress update.");
    }
    onProgress(event);
    if (event.type === "error") {
      throw new Error(event.message || "The check could not be completed.");
    }
    if (event.type === "complete") result = event.result;
  }

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    buffer = buffer.replaceAll("\r\n", "\n");
    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      handleEvent(buffer.slice(0, boundary));
      buffer = buffer.slice(boundary + 2);
      boundary = buffer.indexOf("\n\n");
    }
    if (done) break;
  }
  handleEvent(buffer);

  if (!result) throw new Error("The check ended before returning its results.");
  return result;
}

export function checkAssessor(formData, onProgress = () => {}) {
  return postProgressForm("/api/assessor/check/stream", formData, onProgress);
}

export function checkWriter(formData, onProgress = () => {}) {
  return postProgressForm("/api/writer/check/stream", formData, onProgress);
}
