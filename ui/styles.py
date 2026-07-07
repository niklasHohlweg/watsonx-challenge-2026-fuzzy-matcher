"""
styles — shared button and widget stylesheet constants.

Applied directly via widget.setStyleSheet() so they survive any parent
widget stylesheet scope (QGroupBox, nav bar, etc.) without relying on
objectName ID selectors, which are unreliable when the parent widget has
its own setStyleSheet() call.
"""

BTN_PRIMARY = """
    QPushButton {
        background-color: #1f4e79;
        color: #ffffff;
        border: 1px solid #163354;
        border-radius: 5px;
        padding: 5px 20px;
        font-weight: 700;
        font-size: 13px;
    }
    QPushButton:hover {
        background-color: #1a3f63;
        border-color: #0f2744;
    }
    QPushButton:pressed {
        background-color: #163354;
    }
    QPushButton:disabled {
        background-color: #9ca3af;
        color: #ffffff;
        border-color: #9ca3af;
    }
"""

BTN_SECONDARY = """
    QPushButton {
        background-color: #ffffff;
        color: #1f4e79;
        border: 1px solid #3b82d4;
        border-radius: 5px;
        padding: 5px 20px;
        font-weight: 600;
        font-size: 13px;
    }
    QPushButton:hover {
        background-color: #dbeafe;
        border-color: #1f4e79;
    }
    QPushButton:pressed {
        background-color: #bfdbfe;
    }
    QPushButton:disabled {
        background-color: #f3f4f6;
        color: #9ca3af;
        border-color: #d1d5db;
    }
"""

BTN_DANGER = """
    QPushButton {
        background-color: #ffffff;
        color: #b91c1c;
        border: 1px solid #fca5a5;
        border-radius: 5px;
        padding: 5px 20px;
        font-weight: 600;
        font-size: 13px;
    }
    QPushButton:hover {
        background-color: #fee2e2;
        border-color: #b91c1c;
    }
    QPushButton:pressed {
        background-color: #fecaca;
    }
    QPushButton:disabled {
        background-color: #f3f4f6;
        color: #9ca3af;
        border-color: #d1d5db;
    }
"""
