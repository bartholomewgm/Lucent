// Видео со скруглёнными сглаженными углами и выбором формата картинки.
// Маска повторяет видимую картинку, а не всю область, — поэтому скругляются
// углы самого видео, без чёрных полос вокруг.
import QtQuick
import QtQuick.Effects
import QtMultimedia

Item {
    id: root
    property real radius: 24
    property bool rounded: true          // false — полный экран: без маски, напрямую
    // auto — как снято; fill — заполнить с обрезкой; stretch — растянуть;
    // при forcedAspect > 0 картинка показывается в заданных пропорциях (16:9, 4:3…)
    property string mode: "auto"
    property real forcedAspect: 0
    readonly property bool hasVideo: video.sourceRect.width > 0

    // Подложка на месте будущей картинки, пока видео нет
    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: "#8c000000"
        antialiasing: true
        visible: root.rounded && !root.hasVideo
    }

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
            fillMode: root.mode === "fill" ? VideoOutput.PreserveAspectCrop
                    : root.mode === "auto" ? VideoOutput.PreserveAspectFit
                    : VideoOutput.Stretch
            visible: !root.rounded       // при скруглении видео рисует эффект ниже
            layer.enabled: root.rounded
        }

        Item {
            id: maskShape
            anchors.fill: video
            visible: false
            layer.enabled: true
            layer.smooth: true
            Rectangle {
                // «Авто» — по самой картинке; в остальных режимах она занимает всю область
                readonly property bool fit: root.mode === "auto"
                x: fit ? video.contentRect.x : 0
                y: fit ? video.contentRect.y : 0
                width: fit ? video.contentRect.width : video.width
                height: fit ? video.contentRect.height : video.height
                radius: root.radius
                antialiasing: true
            }
        }

        MultiEffect {
            anchors.fill: video
            source: video
            visible: root.rounded
            maskEnabled: true
            maskSource: maskShape
            maskThresholdMin: 0.5
            maskSpreadAtMin: 1.0          // мягкий край маски — без «лесенки»
        }
    }
}
