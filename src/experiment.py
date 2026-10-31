import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from stego import load_image, save_image, hide, reveal
from metrics import psnr, ssim, changed, lsb_distribution, chi_square

ROOT = os.path.join(os.path.dirname(__file__), "..")
IMAGES_DIR = os.path.join(ROOT, "..")
IMGS = os.path.join(ROOT, "imgs")
RESULTS = os.path.join(ROOT, "results")

PASSWORD = "lab2_password"
IMAGES = ["gradient.png", "my_pic.png", "checkerboard.png", "noise_texture.png"]
LEVELS = [0.01, 0.05]
MAIN_IMAGE = "gradient.png"
MAIN_LEVEL = 0.05

OVERHEAD = 4 + 16 + 12 + 16

BASE_TEXT = (
    "Стеганография - это способ спрятать сам факт передачи сообщения. "
    "В этой лабораторной текст записывается в младшие биты пикселей картинки. "
)

VARIANTS = [
    ("Plain LSB", "plain"),
    ("Encrypted LSB", "encrypted"),
    ("Encrypted Random LSB", "random"),
]


def make_message(n_bytes):
    data = (BASE_TEXT * (n_bytes // len(BASE_TEXT.encode()) + 2)).encode("utf-8")
    data = data[:n_bytes]
    text = data.decode("utf-8", errors="ignore")
    return text.encode("utf-8").ljust(n_bytes, b" ")


def run_one(image_name, level, save_dir=None):
    cover = load_image(os.path.join(IMAGES_DIR, image_name))
    total_bytes = int(cover.size * level) // 8

    rows = []
    stegos = {}

    head = int(cover.size * level)

    p0, p1 = lsb_distribution(cover)
    c, p = chi_square(cover)
    ch, ph = chi_square(cover.reshape(-1)[:head])
    rows.append([image_name, level, "Cover", "", "", 0, 0.0, p0, p1, c, p, ch, ph])

    for name, mode in VARIANTS:
        if mode == "plain":
            msg = make_message(total_bytes - 4)
        else:
            msg = make_message(total_bytes - OVERHEAD)

        stego = hide(cover, msg, mode, PASSWORD)
        assert reveal(stego, mode, PASSWORD) == msg, "сообщение не совпало!"
        stegos[mode] = stego

        n, ratio = changed(cover, stego)
        p0, p1 = lsb_distribution(stego)
        c, p = chi_square(stego)
        ch, ph = chi_square(stego.reshape(-1)[:head])
        rows.append([image_name, level, name, psnr(cover, stego), ssim(cover, stego),
                     n, ratio, p0, p1, c, p, ch, ph])

    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        save_image(cover, os.path.join(save_dir, "cover.png"))
        save_image(stegos["plain"], os.path.join(save_dir, "stego_plain.png"))
        save_image(stegos["encrypted"], os.path.join(save_dir, "stego_encrypted.png"))
        save_image(stegos["random"], os.path.join(save_dir, "stego_random.png"))

    return rows, cover, stegos


def plot_difference(cover, stego, path):
    diff = np.abs(cover.astype(int) - stego.astype(int))
    diff = (diff.max(axis=2) * 255).astype(np.uint8)

    fig, ax = plt.subplots(1, 3, figsize=(13, 4.5))
    ax[0].imshow(cover)
    ax[0].set_title("cover")
    ax[1].imshow(stego)
    ax[1].set_title("stego (Encrypted Random LSB)")
    ax[2].imshow(diff, cmap="gray")
    ax[2].set_title("|cover - stego| x255")
    for a in ax:
        a.axis("off")
    plt.tight_layout()
    plt.savefig(path, dpi=120)
    plt.close()


def plot_histogram(cover, stego, path):
    h1 = np.bincount(cover.reshape(-1), minlength=256)
    h2 = np.bincount(stego.reshape(-1), minlength=256)
    x = np.arange(256)

    fig, ax = plt.subplots(2, 1, figsize=(11, 7))
    ax[0].plot(x, h1, label="cover", lw=1.5)
    ax[0].plot(x, h2, label="stego", lw=1, ls="--")
    ax[0].set_title("Гистограмма значений компонент (R+G+B)")
    ax[0].set_xlabel("значение")
    ax[0].set_ylabel("количество (лог. шкала)")
    ax[0].set_yscale("log")
    ax[0].legend()

    ax[1].bar(x, h2 - h1, width=1.0, color=["tab:blue" if v % 2 == 0 else "tab:red" for v in x])
    ax[1].set_title("Разность гистограмм stego - cover (синие - чётные, красные - нечётные)")
    ax[1].set_xlabel("значение")
    ax[1].set_ylabel("изменение количества")
    plt.tight_layout()
    plt.savefig(path, dpi=120)
    plt.close()


def main():
    os.makedirs(IMGS, exist_ok=True)
    os.makedirs(RESULTS, exist_ok=True)

    all_rows = []
    for image_name in IMAGES:
        for level in LEVELS:
            save_dir = None
            if level == MAIN_LEVEL:
                save_dir = os.path.join(IMGS, os.path.splitext(image_name)[0])
            rows, cover, stegos = run_one(image_name, level, save_dir)
            all_rows += rows

            if image_name == MAIN_IMAGE and level == MAIN_LEVEL:
                save_image(cover, os.path.join(IMGS, "cover.png"))
                save_image(stegos["plain"], os.path.join(IMGS, "stego_plain.png"))
                save_image(stegos["encrypted"], os.path.join(IMGS, "stego_encrypted.png"))
                save_image(stegos["random"], os.path.join(IMGS, "stego_random.png"))
                plot_difference(cover, stegos["random"], os.path.join(RESULTS, "difference.png"))
                plot_histogram(cover, stegos["random"], os.path.join(RESULTS, "histogram.png"))

    header = ["image", "payload", "variant", "psnr", "ssim", "changed", "changed_ratio",
              "p_lsb0", "p_lsb1", "chi2", "p_value", "chi2_head", "p_value_head"]
    with open(os.path.join(RESULTS, "metrics.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(all_rows)

    for r in all_rows:
        img, lvl, var, ps, ss, n, ratio, p0, p1, c, p, ch, ph = r
        ps = f"{ps:.2f}" if ps != "" else "-"
        ss = f"{ss:.6f}" if ss != "" else "-"
        print(f"{img:18} {lvl:3.0%} {var:21} PSNR={ps:>6} SSIM={ss:>8} "
              f"changed={n:6d} ({ratio:.4%}) P1={p1:.4f} chi2={c:10.2f} p={p:.3g} "
              f"| head: chi2={ch:8.2f} p={ph:.3g}")


if __name__ == "__main__":
    main()
