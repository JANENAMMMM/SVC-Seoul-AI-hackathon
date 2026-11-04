import { spawnSync } from "node:child_process";
import { readFile, rename } from "node:fs/promises";
import { resolve } from "node:path";
export async function trimDemo(input, output) {
  const manifest = JSON.parse(
    await readFile(
      new URL("../node_modules/playwright-core/browsers.json", import.meta.url),
      "utf8",
    ),
  );
  const revision = manifest.browsers.find((b) => b.name === "ffmpeg").revision;
  const ffmpeg =
    process.env.FFMPEG_PATH ||
    resolve(
      process.env.LOCALAPPDATA,
      "ms-playwright",
      `ffmpeg-${revision}`,
      "ffmpeg-win64.exe",
    );
  const probe = spawnSync(ffmpeg, ["-hide_banner", "-i", input], {
    encoding: "utf8",
    windowsHide: true,
  });
  const m = probe.stderr?.match(/Duration: (\d+):(\d+):(\d+\.\d+)/);
  if (!m)
    throw Error(
      "녹화 길이를 확인할 수 없습니다. Playwright FFmpeg 경로를 확인하세요.",
    );
  const duration = Number(m[1]) * 3600 + Number(m[2]) * 60 + Number(m[3]);
  const temporary = output + ".trimmed.webm";
  const result = spawnSync(
    ffmpeg,
    [
      "-hide_banner",
      "-y",
      "-i",
      input,
      "-ss",
      String(Math.max(0, duration - 55)),
      "-t",
      "55",
      "-map",
      "0:v:0",
      "-c",
      "copy",
      temporary,
    ],
    { encoding: "utf8", windowsHide: true },
  );
  if (result.status !== 0) throw Error("시연 영상 길이 정리에 실패했습니다.");
  await rename(temporary, output);
  console.log(
    "Demo clip trimmed to approximately 55 seconds (startup loading excluded).",
  );
}
if (process.argv.includes("--existing"))
  await trimDemo(
    resolve("artifacts/bangeoreum-demo-55s.webm"),
    resolve("artifacts/bangeoreum-demo-55s.webm"),
  );
