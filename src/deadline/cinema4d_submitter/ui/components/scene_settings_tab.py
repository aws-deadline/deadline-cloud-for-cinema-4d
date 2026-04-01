# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
import os

from qtpy.QtCore import QSize, Qt  # type: ignore
from qtpy.QtWidgets import (  # type: ignore
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from deadline.client.ui.widgets.job_timeouts_widget import TimeoutTableWidget

from ...takes import TakeSelection
from ...enums import ErrorChecking, TextCaching

"""
UI widgets for the Scene Settings tab.
"""


class FileSearchLineEdit(QWidget):
    """
    Widget used to contain a line edit and a button which opens a file search box.
    """

    def __init__(self, file_format=None, directory_only=False, parent=None):
        super().__init__(parent=parent)

        if directory_only and file_format is not None:
            raise ValueError("Cannot specify file_format when directory_only is True")

        self.file_format = file_format
        self.directory_only = directory_only

        lyt = QHBoxLayout(self)
        lyt.setContentsMargins(0, 0, 0, 0)

        self.edit = QLineEdit(self)
        self.edit.setMaxLength(32767)
        self.btn = QPushButton("...", parent=self)
        self.btn.setMaximumSize(QSize(100, 40))
        self.btn.clicked.connect(self.get_file)

        lyt.addWidget(self.edit)
        lyt.addWidget(self.btn)

    def get_file(self):
        """
        Open a file picker to allow users to choose a file.
        """
        if self.directory_only:
            new_txt = QFileDialog.getExistingDirectory(
                self,
                "Open Directory",
                self.edit.text(),
                QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks,
            )
        else:
            new_txt, _ = QFileDialog.getOpenFileName(self, "Select File", self.edit.text())

        if new_txt:
            self.edit.setText(new_txt)

    def setText(self, txt: str) -> None:  # pylint: disable=invalid-name
        """
        Sets the text of the internal line edit
        """
        self.edit.setText(txt)

    def text(self) -> str:
        """
        Retrieves the text from the internal line edit.
        """
        return self.edit.text()


class SceneSettingsWidget(QWidget):
    """
    Widget containing all top level scene settings.
    """

    def __init__(self, initial_settings, parent=None):
        super().__init__(parent=parent)

        self.developer_options = (
            os.environ.get("DEADLINE_ENABLE_DEVELOPER_OPTIONS", "").upper() == "TRUE"
        )
        # Save the two lists of selectable cameras
        self._build_ui(initial_settings)
        self._configure_settings(initial_settings)

    def _build_ui(self, settings):
        lyt = QGridLayout(self)

        widget_row = 1

        self.op_path_chck = QCheckBox("Override Output Path", self)
        self.op_path_txt = FileSearchLineEdit(directory_only=True)
        lyt.addWidget(self.op_path_chck, widget_row, 0)
        lyt.addWidget(self.op_path_txt, widget_row, 1)
        self.op_path_chck.stateChanged.connect(self.activate_path_changed)
        widget_row += 1

        self.op_multi_path_chck = QCheckBox("Override Multi-Pass Path", self)
        self.op_multi_path_txt = FileSearchLineEdit(directory_only=True)
        lyt.addWidget(self.op_multi_path_chck, widget_row, 0)
        lyt.addWidget(self.op_multi_path_txt, widget_row, 1)
        self.op_multi_path_chck.stateChanged.connect(self.activate_multi_path_changed)
        widget_row += 1

        self.layers_box = QComboBox(self)
        layer_items = [
            (TakeSelection.MAIN, "Main Take"),
            (TakeSelection.ALL, "All Takes"),
            (TakeSelection.MARKED, "Marked Takes"),
            (TakeSelection.CURRENT, "Current Take"),
        ]
        for layer_value, text in layer_items:
            self.layers_box.addItem(text, layer_value)
        lyt.addWidget(QLabel("Takes"), widget_row, 0)
        lyt.addWidget(self.layers_box, widget_row, 1)
        widget_row += 1

        self.frame_override_chck = QCheckBox("Override Frame Range", self)
        self.frame_override_txt = QLineEdit(self)
        self.frame_override_txt.setMaxLength(32767)
        lyt.addWidget(self.frame_override_chck, widget_row, 0)
        lyt.addWidget(self.frame_override_txt, widget_row, 1)
        self.frame_override_chck.stateChanged.connect(self.activate_frame_override_changed)
        widget_row += 1

        self.activate_error_checking_chck = QCheckBox("Activate automatic error checking", self)
        lyt.addWidget(self.activate_error_checking_chck, widget_row, 0)
        widget_row += 1

        self.activate_detailed_logging_chck = QCheckBox("Activate detailed logging", self)
        lyt.addWidget(self.activate_detailed_logging_chck, widget_row, 0)
        widget_row += 1

        self.timeout_settings_box = TimeoutTableWidget(timeouts=settings.timeouts, parent=self)
        lyt.addWidget(self.timeout_settings_box, widget_row, 0, 1, 2)
        widget_row += 1

        # Create a group box for the export job bundle option
        export_group_box = QGroupBox("Cinema 4D submission options", self)
        export_layout = QVBoxLayout(export_group_box)

        self.export_job_bundle_chck = QCheckBox(
            "Save Cinema 4D project with assets before submission", self
        )
        export_layout.addWidget(self.export_job_bundle_chck)

        warning_label = QLabel(
            "Prevents missing file errors during rendering by creating a temporary copy of your project with all assets "
            "and fixing file paths before submission. Uses more disk space and submission time."
        )
        warning_label.setWordWrap(True)
        export_layout.addWidget(warning_label)
        lyt.addWidget(export_group_box, widget_row, 0, 1, 2)
        widget_row += 1

        # Chunking group box
        chunking_group_box = QGroupBox("Task Chunking", self)
        chunking_layout = QGridLayout(chunking_group_box)

        chunking_layout.addWidget(QLabel("Frames per chunk"), 0, 0)
        self.chunk_size_spin = QSpinBox(self)
        # Min 1 (no chunking, one frame per task).
        # Max 150 is the Deadline Cloud service limit for defaultTaskCount.
        # https://docs.aws.amazon.com/deadline-cloud/latest/userguide/deadline-cloud-quotas.html
        self.chunk_size_spin.setMinimum(1)
        self.chunk_size_spin.setMaximum(150)
        self.chunk_size_spin.setValue(1)
        self.chunk_size_spin.setToolTip(
            "Number of frames to group into each chunk.\n"
            "Use 1 for one frame per task (default).\n"
            "Higher values reduce per-task overhead.\n"
            "When Target chunk duration is set, this value is used\n"
            "only as the initial chunk size."
        )
        chunking_layout.addWidget(self.chunk_size_spin, 0, 1)

        chunking_layout.addWidget(QLabel("Target chunk duration"), 1, 0)
        self.target_chunk_duration_spin = QSpinBox(self)
        # Min 0 (use fixed chunk size). Max 3600 (1 hour),
        # a practical upper bound since chunking targets short-running tasks.
        self.target_chunk_duration_spin.setMinimum(0)
        self.target_chunk_duration_spin.setMaximum(3600)
        self.target_chunk_duration_spin.setValue(0)
        self.target_chunk_duration_spin.setSuffix(" seconds")
        self.target_chunk_duration_spin.valueChanged.connect(self._on_duration_changed)
        self.target_chunk_duration_spin.setToolTip(
            "Target render time per chunk. Deadline Cloud will\n"
            "automatically adjust how many frames are grouped\n"
            "together to hit this target. Set to 0 to always use\n"
            "the fixed frames-per-chunk value above."
        )
        chunking_layout.addWidget(self.target_chunk_duration_spin, 1, 1)

        self.chunking_disabled_label = QLabel("Not available when tile rendering is enabled")
        self.chunking_disabled_label.setStyleSheet("color: gray; font-style: italic;")
        self.chunking_disabled_label.setVisible(False)
        chunking_layout.addWidget(self.chunking_disabled_label, 2, 0, 1, 2)

        lyt.addWidget(chunking_group_box, widget_row, 0, 1, 2)
        widget_row += 1

        # Tile Rendering group box
        tile_group_box = QGroupBox("Tile Rendering", self)
        tile_layout = QGridLayout(tile_group_box)

        self.tile_rendering_chck = QCheckBox("Enable Tile Rendering", self)
        tile_layout.addWidget(self.tile_rendering_chck, 0, 0, 1, 2)

        tile_layout.addWidget(QLabel("Columns"), 1, 0)
        self.tiles_columns_spin = QSpinBox(self)
        self.tiles_columns_spin.setMinimum(1)
        # We added limits for now to keep it under 10k tasks for a single take.
        # As 100 * 100 = 10k + 1 task for reassembly goes over 10k limit.
        self.tiles_columns_spin.setMaximum(99)
        self.tiles_columns_spin.setValue(2)
        tile_layout.addWidget(self.tiles_columns_spin, 1, 1)

        tile_layout.addWidget(QLabel("Rows"), 2, 0)
        self.tiles_rows_spin = QSpinBox(self)
        self.tiles_rows_spin.setMinimum(1)
        self.tiles_rows_spin.setMaximum(99)
        self.tiles_rows_spin.setValue(2)
        tile_layout.addWidget(self.tiles_rows_spin, 2, 1)

        self.tile_disabled_label = QLabel("Not available when frames per chunk is greater than 1")
        self.tile_disabled_label.setStyleSheet("color: gray; font-style: italic;")
        self.tile_disabled_label.setVisible(False)
        tile_layout.addWidget(self.tile_disabled_label, 3, 0, 1, 2)

        self.tile_rendering_chck.stateChanged.connect(self.activate_tile_rendering_changed)

        # Chunking and tile rendering are mutually exclusive
        self.chunk_size_spin.valueChanged.connect(self._on_chunk_size_changed)

        lyt.addWidget(tile_group_box, widget_row, 0, 1, 2)
        widget_row += 1

        rendering_options_box = QGroupBox("Cinema 4D rendering options", self)
        rendering_options_layout = QVBoxLayout(rendering_options_box)

        self.use_cached_text_chck = QCheckBox("Use cached text during render", self)
        rendering_options_layout.addWidget(self.use_cached_text_chck)

        use_cached_text_warning_label = QLabel(
            "Prevents incorrect or missing text by using cached fonts. If there are no fonts in the scene, this is "
            "ignored. If there are fonts in the scene, this will increase rendering time."
        )
        use_cached_text_warning_label.setWordWrap(True)
        rendering_options_layout.addWidget(use_cached_text_warning_label)

        lyt.addWidget(rendering_options_box, widget_row, 0, 1, 2)
        widget_row += 1

        if self.developer_options:
            self.include_adaptor_wheels = QCheckBox(
                "Developer Option: Include Adaptor Wheels", self
            )
            lyt.addWidget(self.include_adaptor_wheels, widget_row, 0)
            widget_row += 1

        lyt.addItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding),
            widget_row,
            0,
        )

    def _configure_settings(self, settings):
        self.op_path_chck.setChecked(settings.override_output_path)
        self.op_path_txt.setEnabled(settings.override_output_path)
        self.op_multi_path_chck.setChecked(settings.override_multi_pass_path)
        self.op_multi_path_txt.setEnabled(settings.override_multi_pass_path)
        self.op_path_txt.setText(settings.output_path)
        self.op_multi_path_txt.setText(settings.multi_pass_path)
        self.frame_override_chck.setChecked(settings.override_frame_range)
        self.frame_override_txt.setEnabled(settings.override_frame_range)
        self.frame_override_txt.setText(settings.frame_list)
        self.activate_error_checking_chck.setChecked(bool(int(settings.activate_error_checking)))
        self.activate_detailed_logging_chck.setChecked(settings.activate_detailed_logging)
        self.use_cached_text_chck.setChecked(bool(int(settings.use_cached_text)))

        index = self.layers_box.findData(settings.take_selection)
        if index >= 0:
            self.layers_box.setCurrentIndex(index)

        self.export_job_bundle_chck.setChecked(settings.export_job_bundle_to_temp)

        self.tile_rendering_chck.setChecked(settings.enable_tile_rendering)
        self.tiles_columns_spin.setValue(settings.tiles_columns)
        self.tiles_rows_spin.setValue(settings.tiles_rows)
        self.tiles_columns_spin.setEnabled(settings.enable_tile_rendering)
        self.tiles_rows_spin.setEnabled(settings.enable_tile_rendering)

        self.chunk_size_spin.setValue(settings.chunk_size)
        self.target_chunk_duration_spin.setValue(settings.target_chunk_duration)

        # Apply mutual exclusion between tile rendering and chunking
        if settings.enable_tile_rendering:
            self.chunk_size_spin.setEnabled(False)
            self.target_chunk_duration_spin.setEnabled(False)
            self.chunking_disabled_label.setVisible(True)
        elif settings.chunk_size > 1:
            self.tile_rendering_chck.setEnabled(False)
            self.tile_disabled_label.setVisible(True)

        if self.developer_options:
            self.include_adaptor_wheels.setChecked(settings.include_adaptor_wheels)

    def update_settings(self, settings):
        """
        Update a scene settings object with the latest values.
        """
        settings.output_path = self.op_path_txt.text()
        settings.multi_pass_path = self.op_multi_path_txt.text()

        settings.override_output_path = self.op_path_chck.isChecked()
        settings.override_multi_pass_path = self.op_multi_path_chck.isChecked()

        settings.override_frame_range = self.frame_override_chck.isChecked()
        settings.frame_list = self.frame_override_txt.text()

        settings.take_selection = self.layers_box.currentData()

        settings.activate_error_checking = (
            ErrorChecking.ACTIVATE.value
            if self.activate_error_checking_chck.isChecked()
            else ErrorChecking.DEACTIVATE.value
        )

        settings.activate_detailed_logging = self.activate_detailed_logging_chck.isChecked()

        settings.use_cached_text = (
            TextCaching.ACTIVATE.value
            if self.use_cached_text_chck.isChecked()
            else TextCaching.DEACTIVATE.value
        )

        self.timeout_settings_box.update_settings(settings.timeouts)

        settings.export_job_bundle_to_temp = self.export_job_bundle_chck.isChecked()

        settings.enable_tile_rendering = self.tile_rendering_chck.isChecked()
        settings.tiles_columns = self.tiles_columns_spin.value()
        settings.tiles_rows = self.tiles_rows_spin.value()

        settings.chunk_size = self.chunk_size_spin.value()
        settings.target_chunk_duration = self.target_chunk_duration_spin.value()

        if self.developer_options:
            settings.include_adaptor_wheels = self.include_adaptor_wheels.isChecked()
        else:
            settings.include_adaptor_wheels = False

    def activate_frame_override_changed(self, state):
        """
        Set the activated/deactivated status of the Frame override text box
        """
        self.frame_override_txt.setEnabled(Qt.CheckState(state) == Qt.CheckState.Checked)

    def activate_path_changed(self, state):
        self.op_path_txt.setEnabled(Qt.CheckState(state) == Qt.CheckState.Checked)

    def activate_multi_path_changed(self, state):
        self.op_multi_path_txt.setEnabled(Qt.CheckState(state) == Qt.CheckState.Checked)

    def activate_tile_rendering_changed(self, state):
        enabled = Qt.CheckState(state) == Qt.CheckState.Checked
        self.tiles_columns_spin.setEnabled(enabled)
        self.tiles_rows_spin.setEnabled(enabled)
        if enabled:
            # Disable chunking when tile rendering is enabled
            self.chunk_size_spin.setValue(1)
            self.target_chunk_duration_spin.setValue(0)
            self.chunk_size_spin.setEnabled(False)
            self.target_chunk_duration_spin.setEnabled(False)
            self.chunking_disabled_label.setVisible(True)
        else:
            self.chunk_size_spin.setEnabled(True)
            self.target_chunk_duration_spin.setEnabled(True)
            self.chunking_disabled_label.setVisible(False)

    def _on_chunk_size_changed(self, value):
        if value > 1:
            # Disable tile rendering when chunking is enabled
            self.tile_rendering_chck.setChecked(False)
            self.tile_rendering_chck.setEnabled(False)
            self.tile_disabled_label.setVisible(True)
        else:
            self.tile_rendering_chck.setEnabled(True)
            self.tile_disabled_label.setVisible(False)

    def _on_duration_changed(self, value):
        self.target_chunk_duration_spin.setSuffix(" second" if value == 1 else " seconds")
