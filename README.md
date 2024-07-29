
# pytest-enhanced-reports

A pytest plugin to capture screenshots, videos and JS logs (similar to Cypress) and attach them to supported test reports.

## Support

### Python
* `>= 3.7`

### Browsers
* **Fully supported** - Chromium based browsers - Chrome, Edge, Brave, Opera, Vivaldi, etc
* **Planned in the future** - Firefox, Safari

### Reporting
* **Fully supported** - [allure-pytest-bdd](https://pypi.org/project/allure-pytest-bdd/)
* **Planned in the future** - [pytest-html](https://pypi.org/project/pytest-html/), [pytest-testrail-client](https://pypi.org/project/pytest-testrail-client/)


## Installation
```bash
pip install pytest-enhanced-reports
```

## Usage

### Setup
The plugin needs a code change to be able to capture data from the webdriver instance. Usually, this is just a few lines added to the webdriver initialization logic.

#### Before plugin integration
```python
@pytest.fixture
def driver():
    driver = webdriver.Chrome()
    yield driver
    driver.quit()
```

#### After plugin integration
```python
@pytest.fixture
def driver(enhance_driver):  # `enhance_driver` is a fixture provided by the plugin
    
    driver = webdriver.Chrome()

    enhanced_driver = None
    try:
        enhanced_driver = enhance_driver(driver)
    except Exception as e:
        logger.error(e)

    yield enhanced_driver if enhanced_driver else driver

    driver.quit()
```

### Configuration
The plugin can be configured through command line arguments and/or environment variables. Either option can be used, but if both are provided for any configuration, the command line argument takes precedence over the environment variable.

The following sets of shell commands are equivalent and do the same thing. These examples ignore any configuration for all other plugins/dependencies.
```bash
# Using only command line arguments
pytest --report_screenshot_capture="error-only" --report_screenshot_dir="~/tests/screenshots" --report_browser_console_log_capture="on_failure"
```

```bash
# Using a combination of command line arguments and environment variables
REPORT_SCREENSHOT_DIR="~/tests/screenshots"
pytest --report_screenshot_capture="error-only"  --report_browser_console_log_capture="on_failure"
```

```bash
# Using only environment variables
REPORT_SCREENSHOT_CAPTURE="error-only"
REPORT_SCREENSHOT_DIR="~/tests/screenshots"
REPORT_BROWSER_CONSOLE_LOG_CAPTURE="on_failure"
pytest
```

The full list of configuration options are listed below.

### Screenshots
| Configuration Option                 | Expected Value                                                                        | Default Value         | Description                                                                                                                                                    |
|--------------------------------------|---------------------------------------------------------------------------------------|-----------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **report_screenshot_capture**        | One of "always", "each_ui_operation", "end_of_each_test", "failed_test_only", "never" | each_ui_operation     | Specifies when to capture screenshots.                                                                                                                         |
| **report_screenshot_width**          | int                                                                                   | 0                     | The expected width of the resized screenshot used in reports. Actual value could be slightly different as it needs to fit the aspect ratio.                    |
| **report_screenshot_height**         | int                                                                                   | 0                     | The expected height of the resized screenshot used in reports. Actual value could be slightly different as it needs to fit the aspect ratio.                   |
| **report_screenshot_resize_percent** | int                                                                                   | 40                    | A percentage by which the screenshot will be resized. This is ignored if screenshot height and width values are also provided. Valid values - 75, 60, 50, etc. |
| **report_screenshot_dir**            | path to directory                                                                     | "reports/screenshots" | If set to True, the element being interacted with will be highlighted before taking the screenshot.                                                            |
| **report_keep_screenshots**          | True or False                                                                         | False                 | If set to True, generated screenshot images will not be deleted after the test run.                                                                            |
| **report_highlighted_screenshot**    | True or False                                                                         | False                 | Used to highlight element and take a screenshot before user's interaction                                                                                      |

### Video Recording
| Configuration Option            | Expected Value    | Default Value    | Description                                                                                                                                                         |
|---------------------------------|-------------------|------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **report_video_recording**      | True or False     | False            | If set to True, a video will be recorded for each test.                                                                                                             |
| **report_video_width**          | int               | 0                | Expected width of the video. Actual value could be different as it needs to fit the aspect ratio.                                                                   |
| **report_video_height**         | int               | 0                | Expected height of the video. Actual value could be different as it needs to fit the aspect ratio.                                                                  |
| **report_video_resize_percent** | int               | 75               | A percentage by which the video frames will be resized. This is ignored if video height and width values are also provided. Valid values - 75, 60, 50, etc.         |
| **report_video_frame_rate**     | int               | 30               | The expected number of frames per second while recording a video. This is applicable only when enough frames were recorded in one second, which is not guaranteed.  |
| **report_video_dir**            | path to directory | "reports/videos" | The path to the directory where video files will be stored.                                                                                                         |
| **report_keep_videos**          | True or False     | False            | If set to True, generated video files will not be deleted after the test run.                                                                                       |

### Browser console outputs
| Configuration Option                   | Expected Value                                                                        | Default Value    | Description                                                 |
|----------------------------------------|---------------------------------------------------------------------------------------|------------------|-------------------------------------------------------------|
| **report_browser_console_log_capture** | One of "always", "each_ui_operation", "end_of_each_test", "failed_test_only", "never" | failed_test_only | Specifies when to capture info from the browser console log |


## Contributing
Just the standard fork, branch, commit, test, push, pull request workflow. Including specifics for the sake of documentation.
- Create a fork of [the repo](https://github.com/NewPage-Solutions-Inc/allure-screenshots) and clone the fork
- Install all dependencies from `requirements.txt`
- Make changes
- When committing changes, `black` and `flake8` will be run automatically to ensure code quality
  - In case they don't run automatically, execute `black . && flake8`
  - `black` will automatically make changes to fix any issues it identifies, however the changes would need to be staged again and committed
  - Any problems highlighted by `flake8` requires manual changes/adjustments
- Run the tests to ensure nothing broke
- Push changes, create a pull request