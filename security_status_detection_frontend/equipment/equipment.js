document.addEventListener('DOMContentLoaded', main);

async function main() {
    // 1. get initial statuses
    let init_status = {
        'running': false,
        'person': 0,
        'no_helmet': 0,
        'no_cloth': 0,
    }
    try {
        var resp = await axios.get("http://localhost:5000/status");
        var data = resp.data;
        init_status.running = data.running;
        init_status.person = data.person;
        init_status.no_helmet = data.no_helmet;
        init_status.no_cloth = data.no_cloth;
    } catch (ex) {
        console.log(ex); // ignore error
    }

    // 2. get DOM elements
    let btn_enable = document.getElementById("btn-enable");
    let btn_disable = document.getElementById("btn-disable");
    let img_frame = document.getElementById("img-frame");
    let num_person = document.getElementById("num-person");
    let num_no_helmet = document.getElementById("num-no-helmet");
    let num_no_cloth = document.getElementById("num-no-cloth");
    let txt_logger = document.getElementById("txt-logger");
    let btn_detect = document.getElementById("btn-detect");
    let btn_save = document.getElementById("btn-save");
    let fileInput = document.getElementById("file-input");


    // 3. bind button events
    btn_enable.onclick = async () => {
        var r = await axios.post("http://localhost:5000/enable");
        console.log(r.data);
        btn_enable.setAttribute('disabled', '');
        btn_disable.removeAttribute('disabled');
    };
    btn_disable.onclick = async () => {
        var r = await axios.post("http://localhost:5000/disable");
        console.log(r.data);
        btn_enable.removeAttribute('disabled');
        btn_disable.setAttribute('disabled', '');
    };

    // 4. apply initial statuses to DOM
    if (init_status.running) {
        console.log('init_status.running');
        btn_enable.setAttribute('disabled', '');
        btn_disable.removeAttribute('disabled');
    }
    if (init_status.person) {
        num_person.innerText = `${init_status.person}`;
    }
    if (init_status.no_helmet) {
        num_no_helmet.innerText = `${init_status.no_helmet}`;
        num_no_helmet.style.color = init_status.no_helmet ? 'red' : '';
    }
    if (init_status.no_cloth) {
        num_no_cloth.innerText = `${init_status.no_cloth}`;
        num_no_cloth.style.color = init_status.no_cloth ? 'red' : '';
    }

    /**
     * 根据给定的 checker 判断是否需要调用 setter
     * @type {(arg: {value: T, checker: (value: T) => boolean, setter: (value: T) => void}) => void}
     */
    function setIfChanged(arg) {
        if (arg && arg.checker && arg.setter) {
            if (arg.checker(arg.value)) {
                arg.setter(arg.value);
            }
        }
    }

    // 5. connect websocket server
    let ws;
    try {
        ws = new WebSocket('ws://localhost:5001');
    } catch (ex) {
        alert(ex);
        return;
    }
    ws.onopen = () => {
        console.log('onopen');
    };
    ws.onmessage = ({ data }) => {
        try {
            let obj = JSON.parse(data);
            console.log(obj);
            switch (obj['type']) {
                case 'image_and_status':
                    setIfChanged({
                        value: `data:image/jpeg;base64,${obj['image']}`,
                        checker: (value) => img_frame.getAttribute('src') !== value,
                        setter: (value) => img_frame.setAttribute('src', value),
                    });
                    setIfChanged({
                        value: obj['person'],
                        checker: (value) => num_person.innerText !== `${value}`,
                        setter: (value) => num_person.innerText = `${value}`,
                    });
                    setIfChanged({
                        value: obj['no_helmet'],
                        checker: (value) => num_no_helmet.innerText !== `${value}`,
                        setter: (value) => { num_no_helmet.innerText = `${value}`; num_no_helmet.style.color = value ? 'red' : ''; },
                    });
                    setIfChanged({
                        value: obj['no_cloth'],
                        checker: (value) => num_no_cloth.innerText !== `${value}`,
                        setter: (value) => { num_no_cloth.innerText = `${value}`; num_no_cloth.style.color = value ? 'red' : ''; },
                    });
                    break;
                case 'status_changed':
                    let msg = `[${obj['created_at']}] 工人: ${obj['person']}，未佩戴安全帽人数: ${obj['no_helmet']}，未穿戴反光衣人数: ${obj['no_cloth']}`;
                    txt_logger.textContent = `${msg}\n${txt_logger.textContent}`;
                    txt_logger.scrollTop = 0;
                    break;
                default:
                    break;
            }
        } catch (ex) {
            alert(ex);
        }
    };
    ws.onclose = () => {
        alert('与后端 Websocket 服务器的连接已断开');
    };


    // 6 图片上传与检测
    fileInput.addEventListener('change', handleFileUpload);

    // 文件上传处理函数
    function handleFileUpload(event) {
        const file = event.target.files[0];
        console.log(file);
        if (file) {
            // 使用 FileReader 读取文件
            const reader = new FileReader();
            reader.onload = function (e) {
                // 将读取的数据设置为 img_frame 的 src 属性
                img_frame.src = e.target.result;
            };

            // 读取文件内容
            reader.readAsDataURL(file);

            btn_detect.removeAttribute('disabled');
        }
    };

    btn_detect.onclick = async () => {
        try {
            // 获取图片数据（获取图像数据的 Base64 编码部分）
            let imageData = img_frame.src.split(',')[1];
            // 补充填充字符 '='
            console.log(imageData.length)
            while (imageData.length % 4) {
                imageData += '=';
            }
            console.log(imageData.length)
            // 发送 POST 请求给后端
            let response = await axios.post("http://localhost:5000/detect_image", { image: imageData }, {
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            // 处理后端返回的数据（根据实际情况修改）
            let obj = response.data;

            // 处理图像数据
            setIfChanged({
                value: `data:image/jpeg;base64,${obj['image']}`,
                checker: (value) => img_frame.getAttribute('src') !== value,
                setter: (value) => img_frame.setAttribute('src', value),
            });

            // 处理工人数量
            setIfChanged({
                value: obj['person'],
                checker: (value) => num_person.innerText !== `${value}`,
                setter: (value) => num_person.innerText = `${value}`,
            });

            // 处理未佩戴安全帽人数
            setIfChanged({
                value: obj['no_helmet'],
                checker: (value) => num_no_helmet.innerText !== `${value}`,
                setter: (value) => {
                    num_no_helmet.innerText = `${value}`;
                    num_no_helmet.style.color = value ? 'red' : '';
                },
            });

            // 处理未穿戴反光衣人数
            setIfChanged({
                value: obj['no_cloth'],
                checker: (value) => num_no_cloth.innerText !== `${value}`,
                setter: (value) => {
                    num_no_cloth.innerText = `${value}`;
                    num_no_cloth.style.color = value ? 'red' : '';
                },
            });

            // 其他处理逻辑根据返回数据的格式进行修改
            console.log(obj);
            btn_save.removeAttribute('disabled');

        } catch (ex) {
            console.error("[ERRO] btn_detect click:", ex);
        }
    };

    // 7 图片下载


    // 绑定保存按钮的点击事件
    btn_save.onclick = () => {
        // 获取当前图像数据
        let currentImageData = img_frame.src;

        // 如果有图像数据，则进行保存
        if (currentImageData) {
            // 将 base64 图像数据解析为 Blob 对象
            let blob = base64ToBlob(currentImageData);

            // 创建下载链接
            let link = document.createElement('a');
            link.href = window.URL.createObjectURL(blob);
            link.download = 'detection_image.jpg';

            // 模拟点击下载链接
            link.click();

            // 释放 URL 对象
            window.URL.revokeObjectURL(link.href);
        } else {
            console.log('No image data to save.');
        }
    };

    // 辅助函数：将 base64 图像数据解析为 Blob 对象
    function base64ToBlob(base64Data) {
        let byteString = atob(base64Data.split(',')[1]);
        let mimeString = base64Data.split(',')[0].split(':')[1].split(';')[0];
        let ab = new ArrayBuffer(byteString.length);
        let ia = new Uint8Array(ab);

        for (let i = 0; i < byteString.length; i++) {
            ia[i] = byteString.charCodeAt(i);
        }

        return new Blob([ab], { type: mimeString });
    }



    // 初始化页面时调用一次，根据默认选项显示或隐藏按钮
    toggleDetectionButtons();

}
// 8.按钮选择
function toggleDetectionButtons() {
    const detectionTypeSelect = document.getElementById('detectionType');
    const videoDetectionElements = document.getElementById('set-video');
    const imageDetectionElements = document.getElementById('set-image');
    console.log(detectionTypeSelect.value)
    // 根据选择的检测类型显示或隐藏相关按钮
    if (detectionTypeSelect.value === 'video') {
        showElements(videoDetectionElements);
        hideElements(imageDetectionElements);
    } else {
        showElements(imageDetectionElements);
        hideElements(videoDetectionElements);
    }
}

function showElements(element) {
    element.style.display = "block"

}

function hideElements(element) {

    element.style.display = 'none';

}