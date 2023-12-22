function showOverlay() {
    const overlay = document.querySelector('.overlay');
    overlay.style.display = 'block';
}

function hideOverlay() {
    const overlay = document.querySelector('.overlay');
    overlay.style.display = 'none';
}

function startDetection() {
    // 显示半透明背景
    showOverlay();

    // 获取用户输入的值
    const source = document.getElementById('source').value;
    const confThres = document.getElementById('confThres').value;
    const iouThres = document.getElementById('iouThres').value;

    // 构建请求数据
    const data = {
        source: source,
        conf_thres: parseFloat(confThres),
        iou_thres: parseFloat(iouThres)
    };

    // 显示进度条
    const progressBar = document.getElementById('progress-bar');
    progressBar.style.width = '0';
    const progressContainer = document.getElementById('progress-container');
    progressContainer.style.display = 'block';

    // 模拟进度的增加
    let progressWidth = 0;
    const interval = setInterval(() => {
        progressWidth += 1;
        progressBar.style.width = `${progressWidth}%`;

        if (progressWidth >= 100) {
            clearInterval(interval);
        }
    }, 300);

    // 发送请求给后端
    fetch('http://localhost:5000/detect_fire', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
    })
    .then(response => response.json())
    .then(data => {
        // 处理后端返回的数据
        console.log('后端返回的数据:', data);
        displayImages(data.images_data);
    })
    .catch((error) => {
        console.error('Error:', error);
    })
    .finally(() => {
        // 隐藏进度条和半透明背景
        progressContainer.style.display = 'none';
        hideOverlay();
    });
}




function displayImages(imagesData) {
    const imageGallery = document.getElementById('imageGallery');

    // 清空原有内容
    imageGallery.innerHTML = '';

    // 遍历图片数据列表并显示图片
    imagesData.forEach(imageData => {
        const img = document.createElement('img');
        img.style.width = '100px'; // 调整图片显示大小
        img.style.margin = '5px'; // 添加一些间距

        // 设置图片 base64 数据
        img.src = `data:image/jpeg;base64, ${imageData.data}`;
        
        // 为每张图片设置点击事件
        img.addEventListener('click', function () {
            showImage(img.src);
        });

        imageGallery.appendChild(img);
    });
}
function showImage(imagePath) {
    // 显示半透明背景
    showOverlay();

    // 获取或创建 overlay 元素
    const overlay = document.getElementById('overlay');
    overlay.id = 'overlay';
    overlay.innerHTML = ''; // 清空之前的子元素

    // 创建放大的图片
    const enlargedImage = document.createElement('img');
    enlargedImage.src = imagePath;
    enlargedImage.alt = 'Enlarged Image';
    enlargedImage.style.maxWidth = '60%';
    enlargedImage.style.maxHeight = '60%';

    // 设置样式使图片居中显示
    enlargedImage.style.display = 'block';
    enlargedImage.style.margin = 'auto';
    enlargedImage.style.position = 'absolute';
    enlargedImage.style.top = '50%';
    enlargedImage.style.left = '40%';
    enlargedImage.style.transform = 'translateY(-50%)';
    // 将元素添加到 overlay 中
    overlay.appendChild(enlargedImage);


    // 点击 overlay 区域取消展示
    overlay.onclick = function (event) {
        overlay.innerHTML = ''; // 清空之前的子元素
        if (event.target === overlay) {
            hideOverlay();
        }
    };
}


