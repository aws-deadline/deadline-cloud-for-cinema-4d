# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from typing import List, Optional, Tuple

from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QCheckBox,
    QMessageBox,
)


class FontWarningDialog(QDialog):
    """
    Dialog to display font-related warnings to users before job submission.
    Allows users to review font issues and decide whether to continue with submission.
    """

    def __init__(self, font_errors: List[str], parent: Optional[QDialog] = None):
        super().__init__(parent)
        self.font_errors = font_errors
        self.continue_submission = False
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Font Issues Detected")
        self.setMinimumSize(500, 400)
        self.setModal(True)

        layout = QVBoxLayout(self)

        # Header message
        header_label = QLabel(
            f"Found {len(self.font_errors)} font-related issue(s) in your scene:"
        )
        header_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(header_label)

        # Error details
        error_text = QTextEdit()
        error_text.setReadOnly(True)
        error_text.setMaximumHeight(200)
        
        error_content = ""
        for i, error in enumerate(self.font_errors, 1):
            error_content += f"{i}. {error}\n\n"
        
        error_text.setPlainText(error_content.strip())
        layout.addWidget(error_text)

        # Information message
        info_label = QLabel(
            "These font issues may cause rendering problems on the farm. "
            "Consider fixing the font paths or ensuring fonts are available on render nodes."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; margin: 10px 0;")
        layout.addWidget(info_label)



        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_button = QPushButton("Cancel Submission")
        cancel_button.clicked.connect(self.reject)
        
        continue_button = QPushButton("Continue Anyway")
        continue_button.clicked.connect(self.accept)
        
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(continue_button)
        
        layout.addLayout(button_layout)

    def accept(self):
        self.continue_submission = True
        super().accept()

    def reject(self):
        self.continue_submission = False
        super().reject()

    @staticmethod
    def show_font_warnings(font_errors: List[str], parent: Optional[QDialog] = None) -> Tuple[bool, bool]:
        """
        Static method to show font warnings dialog.
        
        Args:
            font_errors: List of font error messages
            parent: Parent widget
            
        Returns:
            tuple: (continue_submission: bool, unused: bool)
        """
        if not font_errors:
            return True, False
            
        dialog = FontWarningDialog(font_errors, parent)
        dialog.exec_()
        return dialog.continue_submission, False
    