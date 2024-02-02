# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# style based on redshift c4d qt ui emulation

C4D_STYLE = """
/* Redshift Rendering Technologies */
/* Cinema 4D Dark theme emulation */

QWidget
{
    color: #b1b1b1;
    background-color: #222222; /* General Background */
    background: #222222; /* General Background */
}

QWidget:disabled
{
    color: #676767;
    background-color: #272726;
}

QToolBar
{
    border: 1px;
}

QToolBar::handle
{
     spacing: 3px;
     background: transparent;
}

QToolButton
{
}

QToolButton:hover
{
    background-color: #616161;
}

QToolButton:checked
{
    background-color: #222222; /* $COLOR_ICONS_BG_ACTIVE$;*/
}

QToolButton:hover:checked
{
    background-color: #222222; /* $COLOR_ICONS_BG_ACTIVE_HIGHLIGHT$;*/
}

/* Non-popup buttons */
QToolButton[popupMode="0"]
{
    border: 0px; /* Disable border which also adds a checkered pattern to :checked*/
    spacing: 0px; /* Remove extra spacing */
}

QToolButton:pressed {
    background-color: #a0bfe5;
}


QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QPlainTextEdit, QDateTimeEdit
{
    border: 1px solid #878787;
    background: #222222;
    border-top-color: #525252;
    border-left-color: #666666;
    border-bottom-color: #515151;
    border-right-color: #3f3f3f;

    border-top-left-radius: 2px;
    border-bottom-left-radius: 2px;
    padding-left: 2;
    padding-right: 2;
    padding-bottom:1;
    selection-background-color: #a5a5a5;
    selection-color: black;
}

QComboBox, QPushButton
{
    border: 1px solid #343434;
    border-left-color: #303030 ;
    border-bottom-color: #515151;
    border-right-color: #3f3f3f;

    /*background: #6b6b6b;*/
    background: #3b3b3b;
    border-radius: 4px;
    color: #cccccc;
}

QPushButton
{
    padding: 2px 1px 2px 1px;
    border-radius: 9px;
    min-width: 3em;
}

/* Combo Drop-Down etc. */
QAbstractItemView
{
    selection-background-color: #a5a5a5;
    selection-color: black;
    border: 1px solid #222222;
    border-radius: 3px;
}

QComboBox
{
    padding: 1px 1px 1px 6px;
    min-width: 6em;
}


QComboBox:editable
{

}

QComboBox:!editable, QComboBox::drop-down:editable
{

}

/* QComboBox gets the "on" state when the popup is open */
QComboBox:!editable:on, QComboBox::drop-down:editable:on
{

}

QComboBox:on
{
    background: #222222;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 15px;

    border-top-right-radius: 3px; /* same radius as the QComboBox */
    border-bottom-right-radius: 3px;
}


QComboBox::down-arrow
{
    image: url("/Applications/Maxon Cinema 4D 2024/Redshift/res/qt/images/combo_down.png");
}

QComboBox::down-arrow:on
{

}

QSpinBox::up-button,
QDoubleSpinBox::up-button
{
    image: url("/Applications/Maxon Cinema 4D 2024/Redshift/res/qt/images/spin_up.png");
}

QSpinBox::down-button,
QDoubleSpinBox::down-button
{
    image: url("/Applications/Maxon Cinema 4D 2024/Redshift/res/qt/images/spin_down.png");
}



QTabWidget::pane
{ /* The tab widget frame */
    border-top: 1px solid #666666;
}

QTabWidget::tab-bar
{
    left: 2px; /* move to the right by 2px */
}

QTabBar::tab
{
    border-bottom-color: #666666; /* same as the pane color */
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    min-width: 20ex;
    padding: 2px;
}

QTabBar::tab:selected
{
    background-color: #545a99;
    color: #eeeeee;
    border-top: 1px solid #7e7e7e;
    border-left: 1px solid #757575;
    border-right: 1px solid #565656;
}

QTabBar::tab:!selected
{
    margin-top: 2px; /* make non-selected tabs look smaller */
    background-color: #222222;
    border-top: 1px solid #575757;
    border-left: 1px solid #454545;
    border-right: 1px solid #2f2f2f;
}

QMenuBar::item
{
    background: transparent;
}

QMenuBar::item:selected, QMenu::item:selected
{
    background-color:#999999;
    color:#000000;
}

QProgressBar
{
    border: 1px solid #222222;
    border-bottom: 1px solid  #666666;
    padding : 1px;
    height: 10px;
    color: #6e6e6e;
    text-align: center;
}

QProgressBar::chunk
{
    background-color: #8FACCA;
    width: 1px;
}

QSlider::handle:horizontal
{
    background-color: rgb(189,189,189);
    border: 0px solid #5c5c5c;
    border-radius: 2px;
    width: 6px;
    margin: -9px 0;
}

QSlider::groove:horizontal
{
    background-color: #222222; /*$COLOR_BGEDIT$;*/
    height: 4px;
    border-radius: 2px;
    margin-top: 4px;
    margin-bottom: 4px;
}

/* Color-picker theme tweaks */
ColorPickerWidget QPushButton
{
    outline: none;
    border: 1px solid #3e3e3e;
    background-color: #383838;
    color: #dcdcdc;
    padding: 2px 1px 2px 1px;
    border-radius: 4px;
}

ColorPickerWidget QPushButton:hover
{
     background-color: #313131;
}

ColorPickerWidget QPushButton:checked,
ColorPickerWidget QPushButton:pressed
{
    background-color: #5f8ac1;
}

"""
