"""uiautomator2 adapter: device-side HTTP service, Python client, no Appium.

The session duck-types the injected ``uiautomator2.Device`` object; this
package never imports ``uiautomator2`` itself, so automation-kit stays
installable and testable without it.
"""

from adapters.uia2.element import Uia2Element
from adapters.uia2.session import Uia2Session, Uia2SessionFactory

__all__ = ["Uia2Element", "Uia2Session", "Uia2SessionFactory"]
