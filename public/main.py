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

def load_rgb_image(rgb_path: str) -> np.ndarray:
    img = Image.open(rgb_path)

    if img.mode != "RGB":
        img = img.convert("RGB")

    return np.array(img)

def save_mask_png(mask: np.ndarray, out_path: str):
    mask = mask.astype(np.uint8)
    Image.fromarray(mask).save(out_path)

if __name__ == "__main__":

    # 创建 session
    sess = ort.InferenceSession(
        "marinext_rgb_ema_upscale.onnx",
        providers=['CPUExecutionProvider']
    )
    # 读取图片
    img = load_rgb_image("1_test.png")

    ort_predict = Marinext_ONNX_MaskPredictor(model_paths=["marinext_rgb_ema_upscale.onnx"])
    mask_pred = ort_predict.predict(img)

    save_mask_png(
        mask_pred,
        "./new_mask_test_1.png",)


