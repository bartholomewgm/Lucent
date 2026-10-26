// Видео со скруглёнными сглаженными углами и выбором формата картинки.
// Маска повторяет видимую картинку, а не всю область, — поэтому скругляются
// углы самого видео. Поля вокруг картинки заполняет её размытая копия.
import QtQuick
import QtQuick.Effects
import QtMultimedia

Item {
    id: root
    property real radius: 24
    property bool rounded: true          // false — полный экран: без маски, напрямую
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
    // Вокруг картинки остаются поля (скрыт плейлист, высокое окно, 4:3…)
    readonly property bool hasGaps: hasVideo && rounded && pictureInVideo.width > 0
        && (pictureInVideo.width < width - 2 || pictureInVideo.height < height - 2)

    // Подложка на месте будущей картинки, пока видео нет
    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: "#8c000000"
        antialiasing: true
        visible: root.rounded && !root.hasVideo
    }

    // ----- Поля: размытая копия картинки на всю область (как «эмбиент» у YouTube) -----

    Item {
        id: backdrop
        anchors.fill: parent
        visible: root.hasGaps
        clip: true
        layer.enabled: visible
        layer.effect: MultiEffect {
            maskEnabled: true
            maskSource: backdropMask
            maskThresholdMin: 0.5
            maskSpreadAtMin: 1.0
        }

        MultiEffect {
            // Тот же снимок, что у картинки (fullPicture), увеличенный так, чтобы
            // картинка с запасом закрыла всю область (запас прячет размытые края).
            // Делить слой самого video между двумя эффектами нельзя — картинка ломается
            readonly property rect pic: root.pictureInVideo
            readonly property real k: pic.width > 0
                ? Math.max(root.width / pic.width, root.height / pic.height) * 1.1
                : 1
            source: fullPicture
            width: video.width * k
            height: video.height * k
            // центр картинки — в центр области
            x: root.width / 2 - (pic.x + pic.width / 2) * k
            y: root.height / 2 - (pic.y + pic.height / 2) * k
            // Сильное размытие: в поля попадают цвета из глубины кадра, а не тёмная кромка
            blurEnabled: true
            blur: 1.0
            blurMax: 64
            blurMultiplier: 3.0
            saturation: 0.35
            brightness: 0.05
        }
    }

    Item {
        id: backdropMask
        anchors.fill: parent
        visible: false
        layer.enabled: true
        layer.smooth: true
        Rectangle {
            anchors.fill: parent
            radius: root.radius
            antialiasing: true
        }
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
