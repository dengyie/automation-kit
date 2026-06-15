"""Appium adapter primitives.

The adapter is optional: tests and core imports do not require Appium to be
installed. Provide a driver factory when creating sessions.
"""

from adapters.appium.session import AppiumSession, AppiumSessionFactory

__all__ = ["AppiumSession", "AppiumSessionFactory"]
