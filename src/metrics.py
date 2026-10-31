import numpy as np
from scipy.stats import chi2
from skimage.metrics import peak_signal_noise_ratio, structural_similarity


def psnr(cover, stego):
    return peak_signal_noise_ratio(cover, stego, data_range=255)


def ssim(cover, stego):
    return structural_similarity(cover, stego, channel_axis=2, data_range=255)


def changed(cover, stego):
    n = int(np.count_nonzero(cover != stego))
    return n, n / cover.size


def lsb_distribution(img):
    p1 = float(np.mean(img & 1))
    return 1 - p1, p1


def chi_square(img):
    hist = np.bincount(img.reshape(-1), minlength=256).astype(float)
    even = hist[0::2]
    odd = hist[1::2]
    expected = (even + odd) / 2
    mask = expected > 0
    stat = float(np.sum((even[mask] - expected[mask]) ** 2 / expected[mask]))
    df = int(mask.sum()) - 1
    p = float(chi2.sf(stat, df)) if df > 0 else 1.0
    return stat, p
