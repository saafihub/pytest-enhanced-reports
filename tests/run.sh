rm -rf reports
mkdir -p reports

# run normal tests
#pytest -vv --disable-warnings --alluredir='reports' normal_tests/ --report_browser_console_log_capture='end_of_each_test'

# run plugin tests
pytest -vv --disable-warnings --alluredir='reports' plugin_tests/
