import logging
import os
import re
from typing import Tuple
from PIL import Image

logger = logging.getLogger(__name__)
logger.info("Loaded " + __file__)


def get_resized_resolution(
    width: int, height: int, resize_factor: float
) -> Tuple[int, int]:
    """
    Return custom resolution of an image with width and height given resize factor.
    @param width: Width to resize.
    @param height: Height to resize.
    @param resize_factor: Refactor size of an image in the form of % Ex: 0.1.
    @return: New width and height in Tuple format
    """
    new_width = int(width * resize_factor)
    new_height = int(height * resize_factor)
    return new_width, new_height


def mkdir(dir_name: str):
    """
    Creates a new directory at the specified path.
    @param dir_name: The path of the new directory to be created.
    """
    os.makedirs(dir_name, exist_ok=True)


def delete_dir(dir_path: str):
    """
    Deletes the directory at the specified path.
    If the directory is not empty, the contents will be deleted as well.
    @param dir_path: The path to the directory to delete.
    """
    if os.path.isdir(dir_path):
        for f in os.listdir(dir_path):
            if os.path.isdir(os.path.join(dir_path, f)):
                delete_dir(os.path.join(dir_path, f))
            else:
                os.remove(os.path.join(dir_path, f))
        os.rmdir(dir_path)
        logger.debug(f"Deleted the dir '{dir_path}'")


def delete_files(img_dir: str, file_name=None, extension="png"):
    """
    Deletes all files in the specified path or specified filename from the directory.
    @param img_dir: The path of the directory where the files are located.
    @param file_name: The name of the file to delete from the directory.
    @param extension: The extension of given file.
    """
    if file_name:
        os.remove(os.path.join(img_dir, file_name))
        return

    if not os.path.isdir(img_dir):
        logger.warning(f"Directory '{img_dir}' does not exist")
        return

    for f in os.listdir(img_dir):
        if f.endswith(extension):
            os.remove(os.path.join(img_dir, f))
    logger.debug(f"Files with extension {extension} deleted from {img_dir}")


def clean_filename(value: str) -> str:
    """
    This method replace non word characters with underscore(_) for the string.
    @param value: Modify String value provide as an input.
    @return: Returns the string value.
    """
    # remove the undesirable characters
    return re.sub(r"\W", "_", value)


def fail_silently(func):
    """Decorator that makes sure that any errors/exceptions do not get outside the plugin"""

    def wrapped_func(*args, **kws):
        try:
            return func(*args, **kws)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")

    return wrapped_func


def get_image_resolution(directory: str, file_name=None) -> Tuple[int, int]:
    """
    Return the original resolution of an image for provide file name from the directory or
    by default first image file used from the directory provides for the resolution of an image.
    @param directory: Provide the directory name
    @param file_name: Provide the file name
    @return: Returns the image width and height
    """
    if not file_name:
        img = Image.open(
            os.path.join(
                directory,
                [f for f in os.listdir(directory) if f.endswith(".png")][0],
            )
        )
    else:
        img = Image.open(os.path.join(directory, file_name))
    return img.width, img.height
