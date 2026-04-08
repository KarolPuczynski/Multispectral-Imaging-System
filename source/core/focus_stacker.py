"""
This focus-stacking algorithm was inspired by this description found on StackOverflow:

https://stackoverflow.com/questions/15911783/what-are-some-common-focus-stacking-algorithms

"""


import numpy as np
import cv2



class FocusStacker:
    def __init__(self, gaussian_kernel = 5, laplacian_kernel = 5):

        # note that those kernel must be odd and positive
        self.gaussian_kernel = gaussian_kernel
        self.laplacian_kernel = laplacian_kernel

    def load_images(self, image_paths):
        pass

    def compute_gausssian_blur(self, images):

        blurred_images = []

        for image in images:
            blurred_images.append(cv2.GaussianBlur(image, (self.gaussian_kernel, self.gaussian_kernel), 0))

        return blurred_images
    
    def compute_laplacian_and_gaussian_blur(self, images):

        out_images = []

        for image in images:
            # compute gaussian blur on image
            blurred_image = cv2.GaussianBlur(image, (self.gaussian_kernel, self.gaussian_kernel), 0)
            # compute laplacian on blurred image
            out_images.append(cv2.Laplacian(blurred_image, cv2.CV_64F, ksize=self.laplacian_kernel))

        return out_images

                                  

