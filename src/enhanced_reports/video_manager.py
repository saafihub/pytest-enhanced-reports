import os
from typing import Dict, Any, Tuple

import allure
from allure_commons.types import AttachmentType
from selenium.webdriver.remote.webdriver import WebDriver
from PIL import Image
import cv2

from . import common_utils
from .common_utils import get_image_resolution
from .config import Parameter

import logging

logger = logging.getLogger(__name__)
logger.info("Loaded " + __file__)


class ScreenRecorder:
    def __init__(self, directory: str = "temp/", video_store: str = "videos"):
        self.stop = False
        self.__directory = directory  # This directory will be used to save the frames temporarily
        self.__video_store = (
            video_store  # This will be used to save the recorded video
        )
        self.__desired_resolution: Tuple[int, int] = None
        self.__resize_factor: float = None

    def start_capturing(self, driver: WebDriver):
        """
        This method will start capturing images and saving them on disk under /video folder.
        These images will later be used to stitch together into a video.
        @param driver: Provide instance of a driver
        """
        try:
            count = 0
            common_utils.mkdir(self.__directory)
            while True:
                driver.save_screenshot(
                    self.__directory + f"/vid_frame{count}.png"
                )
                count += 1
                if self.stop:
                    logger.debug(
                        f"Stopping screenshot capture for video. Captured {count} screenshots."
                    )
                    break
        except Exception as error:
            logger.error(
                "An Exception occurred while taking screenshot. " + str(error)
            )

    def create_video_from_images(
        self,
        scenario_info: str,
        location: str,
        video_size: tuple,
        frame_rate: int,
    ) -> str:
        """
        This method will stitch the images under /video directory into a video.
        @param scenario_info: Provide the scenario info
        @param location: path to record a video
        @param video_size: Resolution of an image contains height and width
        @param frame_rate: Provide frame_rate and default is 30
        @return: Return the stitch video path
        """
        fourcc = cv2.VideoWriter_fourcc(*"vp09")
        video_name = f"{location}/{scenario_info}.webm"
        video = cv2.VideoWriter(video_name, fourcc, int(frame_rate), video_size)
        image_files = [
            f for f in os.listdir(self.__directory) if f.endswith(".png")
        ]
        image_files = sorted(
            image_files, key=lambda x: int(os.path.splitext(x)[0])
        )
        for img_file in image_files:
            video.write(
                cv2.resize(
                    cv2.imread(os.path.join(self.__directory, img_file)),
                    video_size,
                )
            )
        video.release()

        logger.debug(
            "Video recording completed. [Video Size: "
            + str(video_size)
            + " - Frame Rate: "
            + str(frame_rate)
            + "]"
        )

        return video_name

    def stop_recording_and_stitch_video(
        self,
        report_options: Dict[Parameter, Any],
        recorder_thread,
        scenario_info,
        attachment_name,
    ):
        """
        This method stop recording and attach stitch video of a scenario
        @param report_options: Provide the report options
        @param recorder_thread: Provide the record thread
        @param scenario_info: Provide the scenario info
        @param attachment_name: Provide the attachment name
        """
        try:
            self.stop = True
            recorder_thread.join()
            video_resize_info = self.get_video_resize_resolution(report_options)
            file_name = self.create_video_from_images(
                scenario_info,
                self.__directory,
                video_resize_info,
                report_options[Parameter.VIDEO_FRAME_RATE],
            )
            allure.attach.file(
                file_name,
                name=attachment_name,
                attachment_type=AttachmentType.WEBM,
            )

            if report_options[Parameter.VIDEO_KEEP_FILES]:
                original_size = get_image_resolution(self.__directory)
                self.create_video_from_images(
                    scenario_info,
                    self.__video_store,
                    original_size,
                    report_options[Parameter.VIDEO_FRAME_RATE],
                )

        except Exception as error:
            logger.error(
                "An Exception occurred while stitching video. " + str(error)
            )
        finally:
            # Now clean the images directory
            common_utils.delete_dir(self.__directory)

    def get_video_resize_resolution(
        self, report_options: Dict[Parameter, Any]
    ) -> Tuple[int, int]:
        """
        Return resize resolution of a Video
        @param report_options: Report options contains default width and height
        @return: Return new width and height in Tuple format
        """
        try:
            directory = self.__directory
            desired_resolution = (
                self.__desired_resolution
                if self.__desired_resolution
                else (
                    report_options[Parameter.VIDEO_WIDTH],
                    report_options[Parameter.VIDEO_HEIGHT],
                )
            )
            resize_factor = (
                self.__resize_factor
                if self.__resize_factor
                else report_options[Parameter.VIDEO_RESIZE_PERCENT] / 100
            )

            if desired_resolution == (0, 0):
                # use the resize factor to calculate the desired resolution from actual resolution of the image
                img = Image.open(
                    os.path.join(
                        directory,
                        [
                            f
                            for f in os.listdir(directory)
                            if f.endswith(".png")
                        ][0],
                    )
                )
                desired_resolution = common_utils.get_resized_resolution(
                    img.width, img.height, resize_factor
                )

            return desired_resolution
        except Exception as error:
            logger.error(
                "An Exception occurred while fetching video resize resolution. "
                + str(error)
            )
            # Now clean the images in temp directory as video stitching has failed
            common_utils.delete_dir(self.__directory)
