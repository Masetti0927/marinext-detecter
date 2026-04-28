import onnxruntime as ort
from PIL import Image
import numpy as np

def TTA(x, reverse_aggregation=False):
    """
    x: numpy array, shape (1,C,H,W)
    return: augmented batch (正向) or aggregated mask (反向)
    """
    if not reverse_aggregation:
        im_list = []
        for k in range(4):
            # 旋转
            im = np.rot90(x[0], k=k, axes=(-2, -1))
            im_list.append(im.copy())
            # 翻转
            im_list.append(np.flip(im, axis=-1).copy())
        return np.stack(im_list)  # (8,C,H,W)

    else:
        im_list = []
        # 输入 x shape = (8,H,W) or (8,1,H,W)
        for k in [3, 2, 1, 0]:
            im_flip = np.flip(x[k * 2 + 1], axis=-1)
            im_rot = np.rot90(im_flip, k=-k, axes=(-2, -1))
            im_list.append(im_rot)

            im_rot2 = np.rot90(x[k * 2], k=-k, axes=(-2, -1))
            im_list.append(im_rot2)
        im_stack = np.stack(im_list)
        # 逐像素投票
        final = np.apply_along_axis(lambda arr: np.bincount(arr.astype(np.int32)).argmax(), axis=0, arr=im_stack)
        return final

class Marinext_ONNX_MaskPredictor:
    def __init__(self, model_paths, use_tta=False, rgb_mean=(0.485, 0.456, 0.406), rgb_std=(0.229, 0.224, 0.225)):
        self.use_tta = use_tta
        self.models = [ort.InferenceSession(p) for p in model_paths]
        self.rgb_mean = np.array(rgb_mean, dtype=np.float32).reshape(1, 1, 3)
        self.rgb_std = np.array(rgb_std, dtype=np.float32).reshape(1, 1, 3)

    def preprocess(self, image: np.ndarray) -> np.ndarray:
        if image.ndim != 3 or image.shape[2] != 3:
            raise ValueError("Expected RGB image")
        # NaN 填充
        if np.isnan(image).any():
            nan_mask = np.isnan(image)
            image = image.copy()
            image[nan_mask] = np.broadcast_to(self.rgb_mean, image.shape)[nan_mask]
        # 归一化
        image = image.astype(np.float32) / 255.0
        image = (image - self.rgb_mean) / self.rgb_std
        # HWC -> CHW -> NCHW
        image = np.transpose(image, (2, 0, 1))[np.newaxis, ...]
        return image

    def predict(self, image: np.ndarray) -> np.ndarray:
        x = self.preprocess(image)
        if self.use_tta:
            x_list = TTA(x)  # 你需要自己实现 TTA numpy 版本
        else:
            x_list = [x]

        all_preds = []
        for sess in self.models:
            preds = []
            for xi in x_list:
                out = sess.run(None, {"input": xi})[0]  # (1,C,H,W)
                # logits -> probs
                probs = np.exp(out) / np.sum(np.exp(out), axis=1, keepdims=True)
                pred = np.argmax(probs, axis=1) + 1  # 保持和原逻辑一致
                preds.append(pred)
            # TTA 反聚合
            pred_final = TTA(preds, reverse_aggregation=True) if self.use_tta else preds[0]
            all_preds.append(pred_final)

        # 多模型投票
        all_preds = np.concatenate(all_preds, axis=0)  # (N_models,H,W)
        final_pred = np.squeeze(np.apply_along_axis(lambda x: np.bincount(x).argmax(), 0, all_preds))
        return final_pred

def load_rgb_image(rgb_path: str, target_size=(240, 240)) -> np.ndarray:
    img = Image.open(rgb_path)
    if img.mode != "RGB":
        img = img.convert("RGB")
    img = img.resize(target_size, Image.BILINEAR)
    return np.array(img)

def save_mask_png(mask: np.ndarray, out_path: str):
    mask = mask.astype(np.uint8)
    Image.fromarray(mask).save(out_path)

if __name__ == "__main__":
    import argparse
    import json
    import os
    import sys

    parser = argparse.ArgumentParser(description="MarineXt ONNX Inference")
    parser.add_argument("--input", required=True, help="Path to input image")
    parser.add_argument("--output", required=True, help="Path to output directory")
    parser.add_argument("--models", required=True, nargs="+", help="Paths to ONNX model files (supports ensemble with multiple models)")
    parser.add_argument("--mode", default="rgb", choices=["rgb", "multichannel"], help="Input mode")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    for mp in args.models:
        if not os.path.exists(mp):
            print(json.dumps({"error": f"Model not found: {mp}"}))
            sys.exit(1)

    if not os.path.exists(args.input):
        print(json.dumps({"error": f"Input not found: {args.input}"}))
        sys.exit(1)

    ort_predict = Marinext_ONNX_MaskPredictor(model_paths=args.models)
    img = load_rgb_image(args.input)
    mask_pred = ort_predict.predict(img)

    mask_path = os.path.join(args.output, "mask.png")
    save_mask_png(mask_pred, mask_path)

    # Compute per-class pixel statistics
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


