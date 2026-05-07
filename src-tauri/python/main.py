import onnxruntime as ort
from PIL import Image
import numpy as np
import os
from glob import glob


# --- Multi-channel band statistics (from new_dataset.py) ---
bands_mean = np.array([0.0582676, 0.05223386, 0.04381474, 0.0357083, 0.03412902,
                       0.03680401, 0.03999107, 0.03566642, 0.03965081, 0.0267993,
                       0.01978911]).astype('float32')

bands_std = np.array([0.03240627, 0.03432253, 0.0354812, 0.0375769, 0.03785412,
                      0.04992323, 0.05884482, 0.05545856, 0.06423746, 0.04211187,
                      0.03019115]).astype('float32')


def TTA(x, reverse_aggregation=False):
    """
    x: numpy array, shape (1,C,H,W) when forward, or list of preds (each (1,H,W)) when reverse
    return: augmented batch (forward) or aggregated mask (reverse)
    """
    if not reverse_aggregation:
        im_list = []
        for k in range(4):
            im = np.rot90(x[0], k=k, axes=(-2, -1))            # (C,H,W)
            im_list.append(im[np.newaxis, ...])                # (1,C,H,W)
            im_list.append(np.flip(im, axis=-1)[np.newaxis, ...])  # (1,C,H,W)
        return np.concatenate(im_list, axis=0)  # (8,C,H,W)

    else:
        im_list = []
        for k in [3, 2, 1, 0]:
            im_flip = np.flip(x[k * 2 + 1], axis=-1)
            im_rot = np.rot90(im_flip, k=-k, axes=(-2, -1))
            im_list.append(im_rot)

            im_rot2 = np.rot90(x[k * 2], k=-k, axes=(-2, -1))
            im_list.append(im_rot2)
        im_stack = np.stack(im_list)
        final = np.apply_along_axis(lambda arr: np.bincount(arr.astype(np.int32)).argmax(), axis=0, arr=im_stack)
        return final


class Marinext_ONNX_MaskPredictor:
    def __init__(self, model_paths, use_tta=True, rgb_mean=(0.485, 0.456, 0.406), rgb_std=(0.229, 0.224, 0.225)):
        self.use_tta = use_tta
        self.models = [ort.InferenceSession(p) for p in model_paths]
        self.rgb_mean = np.array(rgb_mean, dtype=np.float32).reshape(1, 1, 3)
        self.rgb_std = np.array(rgb_std, dtype=np.float32).reshape(1, 1, 3)

    def preprocess(self, image: np.ndarray) -> np.ndarray:
        if image.ndim != 3 or image.shape[2] != 3:
            raise ValueError("Expected RGB image")
        if np.isnan(image).any():
            nan_mask = np.isnan(image)
            image = image.copy()
            image[nan_mask] = np.broadcast_to(self.rgb_mean, image.shape)[nan_mask]
        image = image.astype(np.float32) / 255.0
        image = (image - self.rgb_mean) / self.rgb_std
        image = np.transpose(image, (2, 0, 1))[np.newaxis, ...]
        return image

    def predict(self, image: np.ndarray) -> np.ndarray:
        x = self.preprocess(image)
        if self.use_tta:
            x_list = TTA(x)
        else:
            x_list = np.concatenate([x], axis=0)

        all_preds = []
        for sess in self.models:
            preds = []
            for i in range(x_list.shape[0]):
                xi = x_list[i:i+1]  # (1,C,H,W)
                out = sess.run(None, {"input": xi})[0]  # (1,C,H,W)
                probs = np.exp(out) / np.sum(np.exp(out), axis=1, keepdims=True)
                pred = np.argmax(probs, axis=1) + 1
                preds.append(pred)
            pred_final = TTA(preds, reverse_aggregation=True) if self.use_tta else preds[0]
            all_preds.append(pred_final)

        all_preds = np.concatenate(all_preds, axis=0)
        final_pred = np.squeeze(np.apply_along_axis(lambda x: np.bincount(x).argmax(), 0, all_preds))
        return final_pred


class Marinext_ONNX_MultiChannelMaskPredictor:
    def __init__(self, model_paths, use_tta=True):
        self.use_tta = use_tta
        self.models = [ort.InferenceSession(p) for p in model_paths]
        self.bands_mean = bands_mean.reshape(1, 1, 11)
        self.bands_std = bands_std.reshape(1, 1, 11)

    def preprocess(self, image: np.ndarray) -> np.ndarray:
        if image.ndim != 3 or image.shape[2] != 11:
            raise ValueError(f"Expected 11-channel image (H,W,11), got {image.shape}")
        if np.isnan(image).any():
            nan_mask = np.isnan(image)
            image = image.copy()
            image[nan_mask] = np.broadcast_to(self.bands_mean, image.shape)[nan_mask]
        image = image.astype(np.float32)
        image = (image - self.bands_mean) / self.bands_std
        image = np.transpose(image, (2, 0, 1))[np.newaxis, ...]
        return image

    def predict(self, image: np.ndarray) -> np.ndarray:
        x = self.preprocess(image)
        if self.use_tta:
            x_list = TTA(x)
        else:
            x_list = np.concatenate([x], axis=0)

        all_preds = []
        for sess in self.models:
            preds = []
            for i in range(x_list.shape[0]):
                xi = x_list[i:i+1]
                out = sess.run(None, {"input": xi})[0]
                probs = np.exp(out) / np.sum(np.exp(out), axis=1, keepdims=True)
                pred = np.argmax(probs, axis=1) + 1
                preds.append(pred)
            pred_final = TTA(preds, reverse_aggregation=True) if self.use_tta else preds[0]
            all_preds.append(pred_final)

        all_preds = np.concatenate(all_preds, axis=0)
        final_pred = np.squeeze(np.apply_along_axis(lambda x: np.bincount(x).argmax(), 0, all_preds))
        return final_pred


def load_rgb_image(rgb_path: str, target_size=(240, 240)) -> np.ndarray:
    img = Image.open(rgb_path)
    if img.mode != "RGB":
        img = img.convert("RGB")
    img = img.resize(target_size, Image.BILINEAR)
    return np.array(img)


def load_multichannel_image(input_dir: str, target_size=(240, 240)) -> np.ndarray:
    """
    Load 11 single-band images from a directory and stack into (H,W,11).
    Supports .tif, .tiff, .png files. Files are sorted by name to determine band order.
    """
    exts = (".tif", ".tiff", ".png", ".jpg", ".jpeg")
    files = []
    for root, _dirs, filenames in os.walk(input_dir):
        for fn in filenames:
            if fn.lower().endswith(exts):
                files.append(os.path.join(root, fn))
    files = sorted(files)

    if len(files) != 11:
        raise ValueError(f"Expected 11 band files in {input_dir}, found {len(files)}: {files}")

    bands = []
    for fp in files:
        img = Image.open(fp)
        if img.mode == "L":
            img = img.resize(target_size, Image.BILINEAR)
            bands.append(np.array(img, dtype=np.float32))
        else:
            # Grayscale conversion for RGB/other modes
            img = img.convert("L")
            img = img.resize(target_size, Image.BILINEAR)
            bands.append(np.array(img, dtype=np.float32))

    image = np.stack(bands, axis=-1)  # (H,W,11)
    return image


def save_mask_png(mask: np.ndarray, out_path: str):
    mask = mask.astype(np.uint8)
    Image.fromarray(mask).save(out_path)


if __name__ == "__main__":
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(description="MarineXt ONNX Inference")
    parser.add_argument("--input", required=True, help="Path to input image or directory")
    parser.add_argument("--output", required=True, help="Path to output directory")
    parser.add_argument("--models", required=True, nargs="+", help="Paths to ONNX model files")
    parser.add_argument("--mode", default="rgb", choices=["rgb", "multichannel"], help="Input mode")
    parser.add_argument("--use-tta", action="store_true", default=False, help="Enable test-time augmentation")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    for mp in args.models:
        if not os.path.exists(mp):
            print(json.dumps({"error": f"Model not found: {mp}"}))
            sys.exit(1)

    if not os.path.exists(args.input):
        print(json.dumps({"error": f"Input not found: {args.input}"}))
        sys.exit(1)

    if args.mode == "rgb":
        predictor = Marinext_ONNX_MaskPredictor(model_paths=args.models, use_tta=args.use_tta)
        img = load_rgb_image(args.input)
    else:
        predictor = Marinext_ONNX_MultiChannelMaskPredictor(model_paths=args.models, use_tta=args.use_tta)
        img = load_multichannel_image(args.input)

    mask_pred = predictor.predict(img)

    mask_path = os.path.join(args.output, "mask.png")
    save_mask_png(mask_pred, mask_path)

    unique, counts = np.unique(mask_pred, return_counts=True)
    total_pixels = mask_pred.size
    stats = {}
    class_names = {
        1: "Marine Debris", 2: "Dense Sargassum", 3: "Sparse Floating Algae",
        4: "Natural Organic Material", 5: "Ship", 6: "Oil Spill",
        7: "Marine Water", 8: "Sediment-Laden Water", 9: "Foam",
        10: "Turbid Water", 11: "Shallow Water", 12: "Waves & Wakes",
        13: "Oil Platform", 14: "Jellyfish", 15: "Sea snot"
    }
    for cls_id, cnt in zip(unique.tolist(), counts.tolist()):
        if cls_id == 0:
            continue
        name = class_names.get(cls_id, f"Class_{cls_id}")
        stats[name] = {
            "class_id": cls_id,
            "pixel_count": cnt,
            "percentage": round(cnt / total_pixels * 100, 4)
        }

    result = {
        "mask_path": mask_path,
        "stats": stats,
        "total_pixels": total_pixels,
        "input_path": args.input
    }
    print(json.dumps(result))