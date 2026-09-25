const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");
const sharp = require("sharp");

const ROOT = path.resolve(__dirname, "..");
const ASSETS = path.join(ROOT, "assets");
const APK = path.join(process.env.USERPROFILE, "OneDrive", "Desktop", "PriceWise.apk");
const WORK = path.join(process.env.LOCALAPPDATA || process.env.TEMP, "pw-apk-icon-fix");
const OUT = path.join(WORK, "out");
const UNSIGNED = path.join(WORK, "pricewise-unsigned.apk");
const ALIGNED = path.join(WORK, "pricewise-aligned.apk");
const SIGNED = path.join(WORK, "PriceWise-signed.apk");
const KEYSTORE = path.join(ROOT, "android", "app", "debug.keystore");
const BUILD_TOOLS = "C:\\Users\\KLH\\AppData\\Local\\Android\\Sdk\\build-tools\\36.0.0";

const MAROON = { r: 92, g: 18, b: 40, alpha: 1 };

const dens = {
  mdpi: { launcher: 48, adaptive: 108 },
  hdpi: { launcher: 72, adaptive: 162 },
  xhdpi: { launcher: 96, adaptive: 216 },
  xxhdpi: { launcher: 144, adaptive: 324 },
  xxxhdpi: { launcher: 192, adaptive: 432 },
};

// From aapt2 dump of current Desktop APK
const MAP = {
  ic_launcher: {
    mdpi: "d2.webp",
    hdpi: "MO.webp",
    xhdpi: "qs.webp",
    xxhdpi: "Sn.webp",
    xxxhdpi: "sK.webp",
  },
  ic_launcher_round: {
    mdpi: "yw.webp",
    hdpi: "fq.webp",
    xhdpi: "u5.webp",
    xxhdpi: "j_.webp",
    xxxhdpi: "-6.webp",
  },
  ic_launcher_background: {
    mdpi: "At.webp",
    hdpi: "4k.webp",
    xhdpi: "By.webp",
    xxhdpi: "BZ.webp",
    xxxhdpi: "gS.webp",
  },
  ic_launcher_foreground: {
    mdpi: "Nt.webp",
    hdpi: "13.webp",
    xhdpi: "9Q.webp",
    xxhdpi: "iE.webp",
    xxxhdpi: "5c.webp",
  },
  ic_launcher_monochrome: {
    mdpi: "_l.webp",
    hdpi: "mJ.webp",
    xhdpi: "Yu.webp",
    xxhdpi: "ae.webp",
    xxxhdpi: "IG.webp",
  },
};

async function solidMaroon(size) {
  return sharp({
    create: { width: size, height: size, channels: 4, background: MAROON },
  })
    .webp({ quality: 95 })
    .toBuffer();
}

async function resizeWebp(inputPath, size) {
  return sharp(inputPath)
    .resize(size, size, { fit: "cover" })
    .webp({ quality: 95 })
    .toBuffer();
}

async function main() {
  if (!fs.existsSync(OUT)) {
    throw new Error("Extracted APK missing at " + OUT + " — re-extract first");
  }
  const icon = path.join(ASSETS, "icon.png");
  const fg = path.join(ASSETS, "android-icon-foreground.png");

  for (const [dpi, sizes] of Object.entries(dens)) {
    const launcherBuf = await resizeWebp(icon, sizes.launcher);
    const fgBuf = await resizeWebp(fg, sizes.adaptive);
    const bgBuf = await solidMaroon(sizes.adaptive);

    for (const key of ["ic_launcher", "ic_launcher_round"]) {
      const file = MAP[key][dpi];
      fs.writeFileSync(path.join(OUT, "res", file), launcherBuf);
      console.log("wrote", file, sizes.launcher);
    }
    fs.writeFileSync(path.join(OUT, "res", MAP.ic_launcher_background[dpi]), bgBuf);
    fs.writeFileSync(path.join(OUT, "res", MAP.ic_launcher_foreground[dpi]), fgBuf);
    fs.writeFileSync(path.join(OUT, "res", MAP.ic_launcher_monochrome[dpi]), fgBuf);
    console.log("wrote adaptive layers", dpi);
  }

  // Strip old signature
  const meta = path.join(OUT, "META-INF");
  if (fs.existsSync(meta)) {
    fs.rmSync(meta, { recursive: true, force: true });
  }

  // Zip back (use PowerShell Compress-Archive is zip but may break APK; use jar)
  if (fs.existsSync(UNSIGNED)) fs.unlinkSync(UNSIGNED);
  execFileSync(
    "jar",
    ["cf", UNSIGNED, "-C", OUT, "."],
    { stdio: "inherit", shell: true },
  );

  const zipalign = path.join(BUILD_TOOLS, "zipalign.exe");
  const apksigner = path.join(BUILD_TOOLS, "apksigner.bat");
  if (fs.existsSync(ALIGNED)) fs.unlinkSync(ALIGNED);
  execFileSync(zipalign, ["-f", "4", UNSIGNED, ALIGNED], { stdio: "inherit" });
  if (fs.existsSync(SIGNED)) fs.unlinkSync(SIGNED);
  execFileSync(
    apksigner,
    [
      "sign",
      "--ks",
      KEYSTORE,
      "--ks-pass",
      "pass:android",
      "--key-pass",
      "pass:android",
      "--ks-key-alias",
      "androiddebugkey",
      "--out",
      SIGNED,
      ALIGNED,
    ],
    { stdio: "inherit", shell: true },
  );

  fs.copyFileSync(SIGNED, APK);
  console.log("COPIED_TO_DESKTOP", APK, fs.statSync(APK).size);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
