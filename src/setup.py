from setuptools import setup

NAME = "pytest-enhanced-reports"
VERSION = "1.2.3"

INSTALL_REQUIRES = [
    "selenium >=4.0.0, <4.1.4",
    "pytest >=6.2.5, < 7.0.0",
    "pytest-bdd >=5.0.0, < 6.0.0",
    "python-dotenv >=0.15.0, <1.0.0",
    "Pillow >=8.4.0, <9.0.0",
    "wrapt >=1.14.1, <2.0.0",
    "opencv-python",
]

setup(
    name=NAME,
    version=VERSION,
    description="Enhanced test reports for pytest",
    long_description="A enhanced-allure-report to improve allure report by adding screenshots, videos, browser's "
    "outputs",
    author="NewPage Solutions",
    author_email="InnovationDesk@newpage.io",
    license="MIT",
    packages=["enhanced_reports", "enhanced_reports.report_libs"],
    install_requires=INSTALL_REQUIRES,
    entry_points={"pytest11": ["enhanced_reports = enhanced_reports.core"]},
    classifiers=["Framework :: Pytest"],
)
