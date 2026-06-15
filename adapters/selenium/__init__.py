"""Selenium adapter primitives.

The adapter is optional: tests and core imports do not require Selenium to be
installed. Provide a driver factory when creating sessions.
"""

from adapters.selenium.session import SeleniumSession, SeleniumSessionFactory

__all__ = ["SeleniumSession", "SeleniumSessionFactory"]
