import numpy as np
import cv2

def stack(frames, hypercube_scanning=False, gaussian_kernel=5, laplacian_kernel=5, bit_depth=10):
    if hypercube_scanning:
        num_wavelengths = len(frames[0])
        stacked_sequence = []
        
        for w in range(num_wavelengths):
            w_frames = []
            for z in range(len(frames)):
                w_frames.append(frames[z][w]["frame_data"])
                
            stacked_frame = _lap_focus_stacking(w_frames, N=5, kernel_size=gaussian_kernel, bit_depth=bit_depth)
            
            frame_info = {
                "frame_data": stacked_frame,
                "wavelength": frames[0][w]["wavelength"],
                "exposure_us": frames[0][w]["exposure_us"]
            }
            stacked_sequence.append(frame_info)
            
        return stacked_sequence
    else:
        frame = _lap_focus_stacking(frames, N=5, kernel_size=gaussian_kernel, bit_depth=bit_depth)
        return frame


def _lap_focus_stacking(images, N=5, kernel_size=5, bit_depth=10):
    input_dtype = images[0].dtype
    list_lap_pyramids = []
    for img in images:
        lap_pyr = _get_laplacian_pyramid(img, N)
        list_lap_pyramids.append(lap_pyr)
        
    LP_f = []
    
    bases = np.array([pyr[-1] for pyr in list_lap_pyramids])
    D_N = np.array([_deviation_fast(base, kernel_size) for base in bases])
    E_N = np.array([_entropy_fast(base, kernel_size) for base in bases])
    
    D_max_idx = np.argmax(D_N, axis=0)
    E_max_idx = np.argmax(E_N, axis=0)
    D_min_idx = np.argmin(D_N, axis=0)
    E_min_idx = np.argmin(E_N, axis=0)
    
    cond_max = (D_max_idx == E_max_idx)
    cond_min = (D_min_idx == E_min_idx)
    cond_avg = ~(cond_max | cond_min)
    
    LP_N = np.zeros_like(bases[0])
    
    H, W = cond_max.shape
    I, J = np.ogrid[:H, :W]
    
    LP_N[cond_max] = bases[D_max_idx[cond_max], I[cond_max], J[cond_max]]
    LP_N[cond_min] = bases[D_min_idx[cond_min], I[cond_min], J[cond_min]]
    LP_N[cond_avg] = np.mean(bases, axis=0)[cond_avg]
    
    LP_f.append(LP_N)
    
    for l in reversed(range(0, N)):
        L_l_stack = np.array([pyr[l] for pyr in list_lap_pyramids])
        RE_l = np.array([_region_energy(lap) for lap in L_l_stack])
        RE_max_idx = np.argmax(RE_l, axis=0)
        
        H_l, W_l = RE_max_idx.shape
        I_l, J_l = np.ogrid[:H_l, :W_l]
        
        LP_l = L_l_stack[RE_max_idx, I_l, J_l]
        LP_f.append(LP_l)
        
    fused_img = LP_f[0]
    
    for i in range(1, N + 1):
        fused_img = cv2.pyrUp(fused_img, dstsize=(LP_f[i].shape[1], LP_f[i].shape[0]))
        fused_img += LP_f[i]
        
    if input_dtype == np.uint16:
        max_val = (2 ** bit_depth) - 1
        return np.clip(fused_img, 0, max_val).astype(np.uint16)
    else:
        return np.clip(fused_img, 0, 255).astype(np.uint8)


def _get_laplacian_pyramid(img, N):
    curr_img = img.astype(np.float64)
    lap_pyramids = []
    for _ in range(N):
        down = cv2.pyrDown(curr_img)
        up = cv2.pyrUp(down, dstsize=(curr_img.shape[1], curr_img.shape[0]))
        lap = curr_img - up
        lap_pyramids.append(lap)
        curr_img = down
        
    lap_pyramids.append(curr_img)
    return lap_pyramids


def _deviation_fast(image, kernel_size):
    image = image.astype(np.float64)
    mean_img = cv2.blur(image, (kernel_size, kernel_size))
    mean_sq_img = cv2.blur(np.square(image), (kernel_size, kernel_size))
    return np.maximum(mean_sq_img - np.square(mean_img), 0)


def _entropy_fast(image, kernel_size):
    # Normalize image to 0-255 to calculate entropy accurately for >8-bit inputs
    img_min = image.min()
    img_max = image.max()
    if img_max > img_min:
        img_norm = (image - img_min) / (img_max - img_min) * 255.0
    else:
        img_norm = np.zeros_like(image)
        
    img_u8 = np.clip(img_norm, 0, 255).astype(np.uint8)
    levels, counts = np.unique(img_u8, return_counts=True)
    probabilities = np.zeros((256,), dtype=np.float64)
    probabilities[levels] = counts.astype(np.float64) / counts.sum()
    
    valid_mask = probabilities > 0
    log_probs = np.zeros_like(probabilities)
    log_probs[valid_mask] = np.log(probabilities[valid_mask])
    
    mapped_image = -1.0 * img_u8.astype(np.float64) * log_probs[img_u8]
    
    entropies = cv2.boxFilter(mapped_image, -1, (kernel_size, kernel_size), normalize=False)
    return entropies


def _generating_kernel(a):
    kernel = np.array([0.25 - a / 2.0, 0.25, a, 0.25, 0.25 - a / 2.0])
    return np.outer(kernel, kernel)


def _convolve(image, kernel):
    return cv2.filter2D(src=image.astype(np.float64), ddepth=-1, kernel=np.flip(kernel))


def _region_energy(laplacian):
    kernel = _generating_kernel(0.4)
    return _convolve(np.square(laplacian), kernel)