from pathlib import Path

import shutil

assets_dir = Path(__file__).parent.parent.resolve() / "assets"


def configure_ocr_model():
    ocr_dir = assets_dir / "resource" / "model" / "ocr"
    if ocr_dir.exists() and any(ocr_dir.iterdir()):
        print("Found existing OCR directory, skipping default OCR model import.")
        return

    assets_ocr_dir = assets_dir / "MaaCommonAssets" / "OCR"
    if not assets_ocr_dir.exists():
        print(f"Warning: OCR directory not found and {assets_ocr_dir} does not exist.")
        print("Please download OCR model or init git submodules.")
        exit(1)

    shutil.copytree(
        assets_dir / "MaaCommonAssets" / "OCR" / "ppocr_v6" / "small",
        ocr_dir,
        dirs_exist_ok=True,
    )


if __name__ == "__main__":
    configure_ocr_model()

    print("OCR model configured.")
