// Видео со скруглёнными сглаженными углами и выбором формата картинки.
// Маска повторяет видимую картинку, а не всю область, — поэтому скругляются
// углы самого видео. В полях вокруг картинки виден фон окна.
import QtQuick
import QtQuick.Effects
import QtMultimedia

Item {
    id: root
    property real radius: 24
    property bool rounded: true          // false — полный экран: без маски, напрямую
    property color placeholderColor: "#8c000000"  // подложка, пока видео нет (из темы)
    // auto — как снято; stretch — растянуть;
    // при forcedAspect > 0 картинка показывается в заданных пропорциях (16:9, 4:3…)
    property string mode: "auto"
    property real forcedAspect: 0
    // Пропорции самого видео — из Python (videoSizeChanged), а не из sourceRect:
    // при обрезке sourceRect меняется, и решение «обрезать или нет» зациклилось бы
    property real videoAspect: 0
    readonly property bool hasVideo: video.sourceRect.width > 0
    // «Авто»: если пропорции области почти совпадают с видео (до 8%), чуть подрезаем
    // края вместо тонких полос; при большой разнице (4:3 на широком) оставляем поля
    readonly property real maxSmartCrop: 1.08
    readonly property bool smartFill: {
        if (mode !== "auto" || videoAspect <= 0 || frame.height <= 0)
            return false
        var areaAspect = frame.width / frame.height
        return Math.max(areaAspect / videoAspect, videoAspect / areaAspect) <= maxSmartCrop
    }
    // Видимая картинка внутри VideoOutput (его координаты)
    readonly property rect pictureInVideo: (mode === "auto" && !smartFill)
        ? video.contentRect
        : Qt.rect(0, 0, video.width, video.height)
    // Видимая картинка в координатах всей области — вокруг неё светится фон окна
    readonly property rect pictureRect: Qt.rect(frame.x + pictureInVideo.x, frame.y + pictureInVideo.y,
                                                pictureInVideo.width, pictureInVideo.height)

    // Подложка на месте будущей картинки, пока видео нет
    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: root.placeholderColor
        antialiasing: true
        visible: root.rounded && !root.hasVideo
    }

    // ----- Сама картинка -----

    // Область картинки: вся сцена или прямоугольник заданных пропорций по центру
    Item {
        id: frame
        objectName: "frame"
        anchors.centerIn: parent
        width: root.forcedAspect > 0 ? Math.min(root.width, root.height * root.forcedAspect) : root.width
        height: root.forcedAspect > 0 ? width / root.forcedAspect : root.height

        VideoOutput {
            id: video
            objectName: "video"
            anchors.fill: parent
            fillMode: root.mode !== "auto" ? VideoOutput.Stretch
                    : root.smartFill ? VideoOutput.PreserveAspectCrop
                    : VideoOutput.PreserveAspectFit
        }

        // Полноразмерный снимок для скругления; при скруглении прячет само видео
        ShaderEffectSource {
            id: fullPicture
            anchors.fill: video
            sourceItem: video
            hideSource: root.rounded
            live: true
            visible: false
        }

        Item {
            id: maskShape
            anchors.fill: video
            visible: false
            layer.enabled: true
            layer.smooth: true
            Rectangle {
                x: root.pictureInVideo.x
                y: root.pictureInVideo.y
                width: root.pictureInVideo.width
                height: root.pictureInVideo.height
                radius: root.radius
                antialiasing: true
            }
        }

        MultiEffect {
            id: picture
            anchors.fill: video
            source: fullPicture
            visible: root.rounded
            maskEnabled: true
            maskSource: maskShape
            maskThresholdMin: 0.5
            maskSpreadAtMin: 1.0          // мягкий край маски — без «лесенки»
        }
    }
}
