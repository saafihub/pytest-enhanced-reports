
# Useful when debugging / testing during development

pip uninstall -y enhanced-reports

pip install ../src

# if the first parameter is 'y', delete logs file
if [ "$1" = "y" ]
then
  rm -f ./reports/tests.log
fi

mkdir -p reports
#pytest -vv --disable-warnings --headless=False --report_browser_console_log_capture='always' --alluredir='reports'
pytest -vv --disable-warnings --alluredir='reports' plugin_tests/

