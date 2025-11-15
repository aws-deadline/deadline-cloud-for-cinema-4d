# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from typing import List, Optional

from qtpy.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
)

from ...style import HEADER_LABEL_STYLE


class SubmissionWarningDialog(QDialog):
    """
    Dialog to display warnings to users before job submission.
    Allows users to review issues and decide whether to continue with submission.
    """

    def __init__(
        self, warnings: List[str], title: str = "Issues Detected", parent: Optional[QDialog] = None
    ):
        super().__init__(parent)
        self.warnings = warnings
        self.title = title
        self.continue_submission = False
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle(self.title)
        self.setMinimumSize(500, 400)
        self.setModal(True)

        layout = QVBoxLayout(self)

        # Header message
        header_label = QLabel(f"Found {len(self.warnings)} issue(s) in your scene:")
        header_label.setStyleSheet(HEADER_LABEL_STYLE)
        layout.addWidget(header_label)

        # Error details
        error_text = QTextEdit()
        error_text.setReadOnly(True)
        error_text.setMaximumHeight(200)

        error_content = ""
        for i, warning in enumerate(self.warnings, 1):
            error_content += f"{i}. {warning}\n\n"

        error_text.setPlainText(error_content.strip())
        layout.addWidget(error_text)

        # Information message
        info_label = QLabel(
            "These issues may cause problems during rendering on the farm. "
            "Consider fixing them or ensuring the required resources are available on render nodes."
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
    def show_warnings(
        warnings: List[str], title: str = "Issues Detected", parent: Optional[QDialog] = None
    ) -> bool:
        """
        Static method to show warnings dialog.

        Args:
            warnings: List of warning messages
            title: Dialog title
            parent: Parent widget

        Returns:
            bool: True if user chose to continue, False if cancelled
        """
        if not warnings:
            return True

        dialog = SubmissionWarningDialog(warnings, title, parent)
        dialog.exec_()
        return dialog.continue_submission
