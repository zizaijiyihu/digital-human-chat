// 导入数字人组件（从本地克隆的仓库）
import { DigitalHuman, parseAudioStream } from '../digital-human-component/src/index.js';

// 全局变量
let mediaRecorder;
let recordedChunks = [];
let avatar = null;
let audioRecorder;
let audioChunks = [];

// 会话管理
let currentSessionId = generateSessionId();

// 生成会话 ID
function generateSessionId() {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

// 创建新会话
function createNewSession() {
    currentSessionId = generateSessionId();
    console.log('✅ 创建新会话:', currentSessionId);

    // 清空聊天记录 UI
    const chatLog = document.getElementById('chatLog');
    chatLog.innerHTML = '<div class="empty-hint">暂无对话记录</div>';

    showStatus('已创建新会话', 'success');
}

// 清空当前会话历史
async function clearCurrentSession() {
    try {
        const response = await fetch('/api/conversation/clear', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: currentSessionId
            })
        });

        const data = await response.json();
        if (data.success) {
            console.log('✅ 会话历史已清空');

            // 清空聊天记录 UI
            const chatLog = document.getElementById('chatLog');
            chatLog.innerHTML = '<div class="empty-hint">暂无对话记录</div>';

            showStatus('会话历史已清空', 'success');
        } else {
            console.error('清空会话历史失败:', data.error);
            showStatus('清空失败', 'error');
        }
    } catch (error) {
        console.error('清空会话历史失败:', error);
        showStatus('清空失败', 'error');
    }
}

// DOM 元素
const videoPreview = document.getElementById('videoPreview');
const requestCameraBtn = document.getElementById('requestCamera');
const videoCallBtn = document.getElementById('videoCallBtn');
const recordBtn = document.getElementById('recordBtn');
const audioRecordBtn = document.getElementById('audioRecordBtn');
const recordingIndicator = document.getElementById('recordingIndicator');
const cameraPlaceholder = document.getElementById('cameraPlaceholder');
const status = document.getElementById('status');
const chatLog = document.getElementById('chatLog');
const imageUpload = document.getElementById('imageUpload');
const imagePreview = document.getElementById('imagePreview');
const previewImg = document.getElementById('previewImg');
const clearImageBtn = document.getElementById('clearImage');

// 图片上传相关变量
let selectedImage = null;

// 视频通话模式相关变量
let isInVideoCallMode = false;
let videoCaptureEnabled = false;

// 显示状态消息
function showStatus(message, type = 'info') {
    status.textContent = message;
    status.className = `status active ${type}`;
    console.log(`[${type.toUpperCase()}] ${message}`);
}

// 添加对话记录
function addChatMessage(role, text) {
    const emptyHint = chatLog.querySelector('.empty-hint');
    if (emptyHint) {
        emptyHint.remove();
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${role}`;

    const roleLabel = role === 'user' ? '👤 您' : '🤖 数字人';
    messageDiv.innerHTML = `<strong>${roleLabel}</strong><p>${text}</p>`;

    chatLog.appendChild(messageDiv);
    chatLog.scrollTop = chatLog.scrollHeight;
}

// 初始化数字人
async function initAvatar() {
    try {
        showStatus('正在加载数字人...', 'info');

        // 创建数字人（零配置！）
        avatar = new DigitalHuman({
            container: '#avatar',
            autoStart: 'listening',  // 自动开始聆听模式

            // 事件回调
            onReady: () => {
                showStatus('数字人已就绪！', 'success');
                console.log('✅ 数字人加载完成');
            },

            onSpeakStart: () => {
                console.log('🗣️ 数字人开始说话');
            },

            onSpeakEnd: () => {
                console.log('✅ 数字人说话结束');
                // 说话结束后返回聆听模式
                avatar.startListening();
            },

            onListenStart: () => {
                console.log('👂 数字人进入聆听模式');
            },

            onError: (error) => {
                console.error('❌ 数字人错误:', error);
                showStatus('数字人加载失败: ' + error.message, 'error');
            }
        });

    } catch (error) {
        console.error('❌ 初始化数字人失败:', error);
        showStatus('初始化数字人失败: ' + error.message, 'error');
    }
}

// 初始化摄像头
async function initCamera() {
    try {
        showStatus('正在请求摄像头权限...', 'info');

        const stream = await navigator.mediaDevices.getUserMedia({
            video: { width: 1280, height: 720 },
            audio: true
        });

        videoPreview.srcObject = stream;

        // 隐藏占位符和请求按钮
        cameraPlaceholder.style.display = 'none';
        requestCameraBtn.style.display = 'none';

        // 显示录制按钮并启用
        recordBtn.style.display = 'inline-block';
        recordBtn.disabled = false;

        showStatus('摄像头已就绪，按住按钮开始录制', 'success');

    } catch (error) {
        console.error('❌ 摄像头错误:', error);
        showStatus('无法访问摄像头: ' + error.message, 'error');
    }
}

// 开始录制
function startRecording() {
    try {
        recordedChunks = [];
        const stream = videoPreview.srcObject;

        mediaRecorder = new MediaRecorder(stream, {
            mimeType: 'video/webm;codecs=vp8,opus'
        });

        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                recordedChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = () => {
            sendVideo();
        };

        mediaRecorder.start();
        recordingIndicator.style.display = 'block';
        showStatus('正在录制...', 'info');

    } catch (error) {
        console.error('❌ 录制错误:', error);
        showStatus('录制失败: ' + error.message, 'error');
    }
}

// 停止录制
function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        recordingIndicator.style.display = 'none';
        showStatus('正在发送视频...', 'info');
    }
}

// 发送视频
async function sendVideo() {
    if (recordedChunks.length === 0) {
        showStatus('没有录制内容', 'error');
        return;
    }

    try {
        const blob = new Blob(recordedChunks, { type: 'video/webm' });
        console.log('📹 视频大小:', blob.size, 'bytes');

        const formData = new FormData();
        formData.append('video', blob, 'recording.webm');

        showStatus('正在上传并处理...', 'info');
        addChatMessage('user', '(已发送视频)');

        const response = await fetch('/api/chat', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`请求失败: ${response.status}`);
        }

        const result = await response.json();
        console.log('✅ 响应:', result);

        if (result.success) {
            const text = result.text || '(无文字回复)';
            addChatMessage('avatar', text);

            if (result.hasAudio && result.audio) {
                // 解码音频
                const audioData = Uint8Array.from(atob(result.audio), c => c.charCodeAt(0));
                const audioFormat = result.audioFormat || 'wav';
                const audioBlob = new Blob([audioData], { type: `audio/${audioFormat}` });

                // 播放音频（驱动数字人说话）
                if (avatar) {
                    avatar.speak(audioBlob);
                } else {
                    console.warn('⚠️ 数字人未初始化');
                }

                showStatus('数字人正在说话...', 'success');
            } else {
                showStatus('收到回复（无音频）', 'success');
            }
        } else {
            throw new Error(result.error || '未知错误');
        }

    } catch (error) {
        console.error('❌ 发送失败:', error);
        showStatus('发送失败: ' + error.message, 'error');
    }
}

// 开始音频录制
async function startAudioRecording() {
    try {
        audioChunks = [];

        // 请求麦克风权限
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: true
        });

        audioRecorder = new MediaRecorder(stream, {
            mimeType: 'audio/webm;codecs=opus'
        });

        audioRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };

        audioRecorder.onstop = () => {
            sendAudio();
            // 停止音频流
            stream.getTracks().forEach(track => track.stop());
        };

        audioRecorder.start();
        recordingIndicator.style.display = 'block';
        showStatus('正在录制音频...', 'info');

    } catch (error) {
        console.error('❌ 音频录制错误:', error);
        showStatus('无法访问麦克风: ' + error.message, 'error');
    }
}

// 停止音频录制
function stopAudioRecording() {
    if (audioRecorder && audioRecorder.state !== 'inactive') {
        audioRecorder.stop();
        recordingIndicator.style.display = 'none';
        showStatus('正在发送音频...', 'info');
    }
}

// 发送音频（流式版本）
async function sendAudio() {
    if (audioChunks.length === 0) {
        showStatus('没有录制内容', 'error');
        return;
    }

    try {
        const blob = new Blob(audioChunks, { type: 'audio/webm' });
        console.log('🎤 音频大小:', blob.size, 'bytes');

        const formData = new FormData();
        formData.append('audio', blob, 'recording.webm');

        showStatus('正在上传并处理...', 'info');
        addChatMessage('user', '(已发送音频)');

        // 使用流式 API
        const response = await fetch('/api/audio-chat-streaming', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`请求失败: ${response.status}`);
        }

        console.log('✅ 开始接收流式音频');
        showStatus('数字人正在说话...', 'success');

        // 创建音频流生成器（原始 HTTP 流）
        async function* rawAudioStream() {
            const reader = response.body.getReader();
            let chunkCount = 0;

            while (true) {
                const { done, value } = await reader.read();
                if (done) {
                    console.log(`✅ 流式接收完成，共 ${chunkCount} 个片段`);
                    break;
                }

                chunkCount++;
                console.log(`🔊 收到 HTTP 片段 #${chunkCount}:`, value.byteLength, 'bytes');

                // 返回 ArrayBuffer
                yield value.buffer;
            }
        }

        // ✅ 使用 parseAudioStream 包装，解决 HTTP 分块问题
        const parsedStream = parseAudioStream(rawAudioStream());

        // 使用数字人的流式播放功能
        if (avatar) {
            const controller = await avatar.speakStreaming({
                audioStream: parsedStream,
                onChunkReceived: (chunk) => {
                    console.log('🎵 开始播放音频片段:', chunk.byteLength, 'bytes');
                },
                onStreamEnd: () => {
                    console.log('✅ 数字人说话完成');
                    showStatus('对话完成', 'success');
                }
            });

            console.log('🎙️ 流式播放已启动');
        } else {
            console.warn('⚠️ 数字人未初始化');
            showStatus('数字人未初始化', 'error');
        }

    } catch (error) {
        console.error('❌ 发送失败:', error);
        showStatus('发送失败: ' + error.message, 'error');
    }
}

// 事件监听
requestCameraBtn.addEventListener('click', initCamera);

// 视频录制：按住录制，松开发送
recordBtn.addEventListener('pointerdown', (e) => {
    e.preventDefault();
    startRecording();
});

recordBtn.addEventListener('pointerup', (e) => {
    e.preventDefault();
    stopRecording();
});

recordBtn.addEventListener('pointerleave', (e) => {
    // 如果正在录制时鼠标离开，也停止录制
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        stopRecording();
    }
});

// 防止触摸设备上的默认行为
recordBtn.addEventListener('touchstart', (e) => {
    e.preventDefault();
}, { passive: false });

// 音频录制：按住录制，松开发送
audioRecordBtn.addEventListener('pointerdown', (e) => {
    e.preventDefault();
    startAudioRecording();
});

audioRecordBtn.addEventListener('pointerup', (e) => {
    e.preventDefault();
    stopAudioRecording();
});

audioRecordBtn.addEventListener('pointerleave', (e) => {
    // 如果正在录制时鼠标离开，也停止录制
    if (audioRecorder && audioRecorder.state === 'recording') {
        stopAudioRecording();
    }
});

// 防止触摸设备上的默认行为
audioRecordBtn.addEventListener('touchstart', (e) => {
    e.preventDefault();
}, { passive: false });

// 图片上传事件
imageUpload.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        handleImageUpload(file);
    }
});

// 清除图片按钮
clearImageBtn.addEventListener('click', () => {
    selectedImage = null;
    imagePreview.style.display = 'none';
    previewImg.src = '';
    imageUpload.value = '';
});

// 处理图片上传
async function handleImageUpload(file) {
    try {
        showStatus('正在处理图片...', 'info');

        // 显示预览
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImg.src = e.target.result;
            imagePreview.style.display = 'block';
        };
        reader.readAsDataURL(file);

        // 保存图片用于发送
        selectedImage = file;

        showStatus('图片已上传，正在请求大模型点评...', 'info');

        // 立即发送图片给大模型点评
        await sendImageForCommentary(file);

    } catch (error) {
        console.error('❌ 图片上传失败:', error);
        showStatus('图片上传失败: ' + error.message, 'error');
    }
}

// 发送图片给大模型点评（流式返回）
async function sendImageForCommentary(imageFile) {
    try {
        showStatus('正在请求大模型点评...', 'info');

        // 准备表单数据
        const formData = new FormData();
        formData.append('image', imageFile);

        // 发送请求（流式接口）
        const response = await fetch('/api/image-commentary-streaming', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        showStatus('正在接收大模型点评（流式）...', 'info');

        // 创建音频流生成器（原始 HTTP 流）
        async function* rawAudioStream() {
            const reader = response.body.getReader();
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                yield value.buffer;  // 返回 ArrayBuffer
            }
        }

        // ✅ 使用 parseAudioStream 包装，解决 HTTP 分块问题
        const parsedStream = parseAudioStream(rawAudioStream());

        // 使用流式播放
        const controller = await avatar.speakStreaming({
            audioStream: parsedStream,
            onChunkReceived: (chunk) => {
                console.log('🎵 开始播放音频片段:', chunk.byteLength);
            },
            onStreamEnd: () => {
                console.log('✅ 数字人说话完成');
                showStatus('大模型点评完成！', 'success');
                addChatMessage('avatar', '（已对图片进行点评）');
            }
        });

        addChatMessage('user', '📷 上传了一张图片');

    } catch (error) {
        console.error('❌ 发送图片失败:', error);
        showStatus('发送失败: ' + error.message, 'error');
    }
}

// 视频通话模式切换
async function toggleVideoCallMode() {
    try {
        console.log('🔧 [DEBUG] toggleVideoCallMode 被调用');
        console.log('🔧 [DEBUG] 当前状态 isInVideoCallMode:', isInVideoCallMode);
        console.log('🔧 [DEBUG] avatar 对象:', avatar);

        if (!isInVideoCallMode) {
            // 进入视频通话模式
            console.log('📹 [INFO] 准备进入视频通话模式');
            showStatus('正在请求摄像头和麦克风权限...', 'info');

            console.log('🔧 [DEBUG] 检查 avatar.enterVideoCallMode 方法:', typeof avatar.enterVideoCallMode);

            if (!avatar.enterVideoCallMode) {
                throw new Error('avatar.enterVideoCallMode 方法不存在，请检查 digital-human-component 版本');
            }

            // 进入视频通话模式（会自动请求摄像头和麦克风权限）
            console.log('🔧 [DEBUG] 调用 avatar.enterVideoCallMode...');
            await avatar.enterVideoCallMode({
                pipPosition: 'bottom-right',
                pipScale: 0.25,
                showLocalVideo: true,
                showAudioVisualizer: true
            });

            console.log('✅ [SUCCESS] enterVideoCallMode 调用成功');

            // 启动视频自动采集
            console.log('🔧 [DEBUG] 调用 avatar.enableVideoAutoCapture...');
            await avatar.enableVideoAutoCapture({
                // 视频录制配置
                maxGroups: 1,                   // 保留 1 组背景视频（5秒）
                groupDuration: 5000,            // 每组 5 秒
                maxRecordDuration: 60000,       // 最长录制 60 秒

                // VAD 基础配置（使用最新的默认值）
                speechThreshold: 30,            // 基础阈值（默认 30）
                silenceDuration: 2000,          // 静音 2 秒后停止录制
                minSpeakDuration: 900,          // 最小说话时长 900ms（过滤短声音）

                // VAD 高级配置（使用默认值即可，系统会自动校准）
                calibrationDuration: 3000,      // 校准时长 3 秒
                noiseUpdateInterval: 10000,     // 每 10 秒更新背景噪音
                minThreshold: 20,               // 动态阈值最小值（避免在安静环境下误触发）
                lowThresholdMultiplier: 1.5,    // 预激活阈值倍数
                highThresholdMultiplier: 3.0,   // 确认说话阈值倍数

                onVideoCapture: handleVideoCapture,

                onSpeechStart: () => {
                    console.log('🎤 [INFO] 检测到说话开始');
                    showStatus('正在录制...', 'info');
                },

                onSpeechEnd: () => {
                    console.log('🤐 [INFO] 说话结束');
                },

                onError: (error) => {
                    console.error('❌ [ERROR] 视频自动采集错误:', error);
                    showStatus('采集错误: ' + error.message, 'error');
                }
            });

            console.log('✅ [SUCCESS] enableVideoAutoCapture 调用成功');
            isInVideoCallMode = true;
            videoCallBtn.textContent = '⏹️ 退出视频通话';
            videoCallBtn.classList.add('active');
            showStatus('已进入视频通话模式，开始自动监听...', 'success');

        } else {
            // 退出视频通话模式
            console.log('⏹️ [INFO] 退出视频通话模式');

            // 先停止视频自动采集
            console.log('🔧 [DEBUG] 调用 avatar.disableVideoAutoCapture...');
            if (avatar.disableVideoAutoCapture) {
                avatar.disableVideoAutoCapture();
                console.log('✅ [SUCCESS] 已停止视频自动采集');
            }

            console.log('🔧 [DEBUG] 检查 avatar.exitVideoCallMode 方法:', typeof avatar.exitVideoCallMode);

            if (!avatar.exitVideoCallMode) {
                throw new Error('avatar.exitVideoCallMode 方法不存在');
            }

            avatar.exitVideoCallMode();

            console.log('✅ [SUCCESS] exitVideoCallMode 调用成功');
            isInVideoCallMode = false;
            videoCallBtn.textContent = '📹 进入视频通话';
            videoCallBtn.classList.remove('active');
            showStatus('已退出视频通话模式', 'info');
        }
    } catch (error) {
        console.error('❌ [ERROR] 切换视频通话模式失败:', error);
        console.error('❌ [ERROR] 错误堆栈:', error.stack);
        showStatus('切换失败: ' + error.message, 'error');
    }
}

// 处理视频自动采集（新版：接收视频组数组）
async function handleVideoCapture(videoGroups) {
    try {
        console.log('🎬 [DEBUG] ========== handleVideoCapture 被调用 ==========');
        console.log(`🎬 [DEBUG] 收到 ${videoGroups.length} 个视频组`);

        if (!videoGroups || videoGroups.length === 0) {
            console.warn('⚠️ [WARN] 没有视频组');
            return;
        }

        // 打印每个视频组的详细信息
        videoGroups.forEach((group, index) => {
            console.log(`🎬 [DEBUG] 视频组 ${index + 1}:`, {
                type: group.type,
                duration: `${(group.duration / 1000).toFixed(1)}s`,
                size: `${(group.size / 1024 / 1024).toFixed(2)} MB`,
                startTime: new Date(group.startTime).toLocaleTimeString(),
                endTime: new Date(group.endTime).toLocaleTimeString()
            });
        });

        // 计算总时长
        const totalDuration = videoGroups.reduce((sum, g) => sum + g.duration, 0);
        console.log(`📊 [INFO] 总时长: ${(totalDuration / 1000).toFixed(1)} 秒`);

        showStatus('正在处理视频并发送...', 'info');
        addChatMessage('user', `(自动采集 ${videoGroups.length} 个视频组，共 ${(totalDuration / 1000).toFixed(1)}秒)`);

        // 创建 FormData，发送所有视频组
        const formData = new FormData();

        // 添加会话 ID
        formData.append('session_id', currentSessionId);
        console.log('🔑 [DEBUG] 会话 ID:', currentSessionId);

        if (videoGroups.length > 1) {
            console.log(`🔀 [INFO] 多个视频组（${videoGroups.length} 个），将在后端合并`);
            videoGroups.forEach((group, index) => {
                console.log(`🎬 [DEBUG] 添加视频组 ${index + 1} 到 FormData`);
                formData.append('videos', group.blob, `video-${index + 1}-${group.type}.webm`);
            });
        } else {
            console.log('📹 [INFO] 单个视频组，直接发送');
            formData.append('videos', videoGroups[0].blob, 'video.webm');
        }

        // 调用新的流式 TTS API
        console.log('🌐 [DEBUG] 准备发送 POST 请求到 /api/video-auto-chat-with-tts');

        const response = await fetch('/api/video-auto-chat-with-tts', {
            method: 'POST',
            body: formData
        });

        console.log('🌐 [DEBUG] 收到响应，状态码:', response.status);

        if (!response.ok) {
            const errorText = await response.text();
            console.error('❌ [ERROR] 请求失败:', response.status, errorText);
            throw new Error(`请求失败: ${response.status} - ${errorText}`);
        }

        console.log('✅ 开始接收流式数据（元数据 + 音频）');
        showStatus('正在接收 AI 响应...', 'info');

        // 创建音频流生成器（解析元数据块 + 音频流）
        async function* rawAudioStream() {
            const reader = response.body.getReader();
            let buffer = new Uint8Array(0);
            let metadataParsed = false;
            let audioChunkCount = 0;

            while (true) {
                const { done, value } = await reader.read();
                if (done) {
                    console.log(`✅ 流式接收完成，共 ${audioChunkCount} 个音频片段`);
                    break;
                }

                // 将新数据追加到缓冲区
                const newBuffer = new Uint8Array(buffer.length + value.length);
                newBuffer.set(buffer);
                newBuffer.set(value, buffer.length);
                buffer = newBuffer;

                // 第一步：解析元数据块（只解析一次）
                if (!metadataParsed && buffer.length >= 4) {
                    // 读取元数据长度（4字节，big-endian）
                    const metadataLength = (buffer[0] << 24) | (buffer[1] << 16) | (buffer[2] << 8) | buffer[3];
                    console.log(`📋 [DEBUG] 元数据长度: ${metadataLength} bytes`);

                    // 检查是否已接收完整的元数据
                    if (buffer.length >= 4 + metadataLength) {
                        // 提取元数据
                        const metadataBytes = buffer.slice(4, 4 + metadataLength);
                        const metadataJson = new TextDecoder().decode(metadataBytes);
                        const metadata = JSON.parse(metadataJson);

                        console.log('📋 [INFO] 收到元数据:', metadata);
                        console.log('💬 [INFO] AI 消息:', metadata.message);
                        console.log('📋 [INFO] Actions:', metadata.actions);

                        // 处理 actions
                        if (metadata.actions && metadata.actions.length > 0) {
                            metadata.actions.forEach(action => {
                                console.log(`  ✅ Action: ${action.type}`, action);
                                // TODO: 根据 action.type 执行相应操作
                            });
                        }

                        // 显示消息到聊天记录
                        addChatMessage('avatar', metadata.message);

                        // 移除元数据，剩下的都是音频数据
                        buffer = buffer.slice(4 + metadataLength);
                        metadataParsed = true;

                        console.log('✅ 元数据解析完成，开始接收音频流');
                        showStatus('数字人正在说话...', 'success');
                    }
                }

                // 第二步：返回音频数据（元数据解析后）
                if (metadataParsed && buffer.length > 0) {
                    audioChunkCount++;
                    console.log(`🔊 收到音频片段 #${audioChunkCount}:`, buffer.byteLength, 'bytes');

                    // 返回音频 ArrayBuffer
                    yield buffer.buffer.slice(buffer.byteOffset, buffer.byteOffset + buffer.byteLength);
                    buffer = new Uint8Array(0);  // 清空缓冲区
                }
            }
        }

        // 使用 parseAudioStream 包装，解决 HTTP 分块问题
        const parsedStream = parseAudioStream(rawAudioStream());

        // 使用数字人的流式播放功能
        if (avatar) {
            await avatar.speakStreaming({
                audioStream: parsedStream,
                onChunkReceived: (chunk) => {
                    console.log('🎵 开始播放音频片段:', chunk.byteLength, 'bytes');
                },
                onStreamEnd: () => {
                    console.log('✅ 数字人说话完成');
                    showStatus('对话完成', 'success');
                    addChatMessage('avatar', '(已回复视频内容)');
                }
            });

            console.log('🎙️ 流式播放已启动');
        } else {
            console.warn('⚠️ 数字人未初始化');
            showStatus('数字人未初始化', 'error');
        }

    } catch (error) {
        console.error('❌ 处理视频采集失败:', error);
        showStatus('处理失败: ' + error.message, 'error');
    } finally {
        // 无论成功还是失败，都尝试加载最新视频到预览区域
        loadLatestVideos();
    }
}

// ========== 视频预览功能 ==========

/**
 * 加载最新的视频到预览区域
 */
async function loadLatestVideos() {
    try {
        console.log('🎬 加载最新视频...');

        const response = await fetch('/api/latest-videos');
        const data = await response.json();

        if (data.error) {
            console.log('ℹ️ 暂无视频');
            return;
        }

        console.log('✅ 收到视频数据:', data);

        // 显示原始片段
        const segmentContainer = document.getElementById('segmentVideos');
        segmentContainer.innerHTML = ''; // 清空现有内容

        if (data.segments && data.segments.length > 0) {
            data.segments.forEach((segment, index) => {
                const videoItem = document.createElement('div');
                videoItem.className = 'video-item';

                // 类型标签样式
                const typeLabel = segment.type === 'before-speaking' ?
                    '<span style="color: #8b5cf6;">🔵 背景片段</span>' :
                    segment.type === 'speaking' ?
                    '<span style="color: #10b981;">🔴 说话片段</span>' :
                    '<span style="color: #6b7280;">⚪ 未知</span>';

                videoItem.innerHTML = `
                    <h4>片段 ${index + 1} - ${typeLabel}</h4>
                    <video controls>
                        <source src="${segment.url}" type="video/mp4">
                        您的浏览器不支持视频播放
                    </video>
                `;
                segmentContainer.appendChild(videoItem);
            });
        } else {
            segmentContainer.innerHTML = '<p class="empty-hint">暂无视频片段</p>';
        }

        // 显示合并后的视频
        const mergedContainer = document.getElementById('mergedVideo');
        mergedContainer.innerHTML = ''; // 清空现有内容

        if (data.merged) {
            const videoItem = document.createElement('div');
            videoItem.className = 'video-item';
            videoItem.innerHTML = `
                <h4>合并后的完整视频</h4>
                <video controls>
                    <source src="${data.merged.url}" type="video/mp4">
                    您的浏览器不支持视频播放
                </video>
            `;
            mergedContainer.appendChild(videoItem);
        } else {
            mergedContainer.innerHTML = '<p class="empty-hint">暂无合并视频</p>';
        }

        console.log('✅ 视频加载完成');

    } catch (error) {
        console.error('❌ 加载视频失败:', error);
    }
}

// ========== 系统设置功能 ==========

const settingsBtn = document.getElementById('settingsBtn');
const settingsModal = document.getElementById('settingsModal');
const closeSettings = document.getElementById('closeSettings');
const cancelSettings = document.getElementById('cancelSettings');
const saveSettings = document.getElementById('saveSettings');
const systemPromptInput = document.getElementById('systemPrompt');

/**
 * 打开设置弹窗
 */
async function openSettings() {
    try {
        // 加载当前的系统提示词
        const response = await fetch('/api/system-prompt');
        const data = await response.json();

        systemPromptInput.value = data.prompt || '';
        settingsModal.style.display = 'flex';

        console.log('✅ 设置弹窗已打开');
    } catch (error) {
        console.error('❌ 加载系统提示词失败:', error);
        showStatus('加载设置失败', 'error');
    }
}

/**
 * 关闭设置弹窗
 */
function closeSettingsModal() {
    settingsModal.style.display = 'none';
}

/**
 * 保存设置
 */
async function saveSystemSettings() {
    try {
        const prompt = systemPromptInput.value.trim();

        if (!prompt) {
            showStatus('提示词不能为空', 'error');
            return;
        }

        const response = await fetch('/api/system-prompt', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ prompt })
        });

        const data = await response.json();

        if (data.success) {
            showStatus('设置已保存', 'success');
            closeSettingsModal();
            console.log('✅ 系统提示词已更新:', data.prompt);
        } else {
            throw new Error(data.error || '保存失败');
        }

    } catch (error) {
        console.error('❌ 保存设置失败:', error);
        showStatus('保存失败: ' + error.message, 'error');
    }
}

// 设置按钮事件
settingsBtn.addEventListener('click', openSettings);
closeSettings.addEventListener('click', closeSettingsModal);
cancelSettings.addEventListener('click', closeSettingsModal);
saveSettings.addEventListener('click', saveSystemSettings);

// 点击弹窗外部关闭
settingsModal.addEventListener('click', (e) => {
    if (e.target === settingsModal) {
        closeSettingsModal();
    }
});

// 视频通话按钮事件
videoCallBtn.addEventListener('click', toggleVideoCallMode);

// 会话管理按钮事件
const newSessionBtn = document.getElementById('newSessionBtn');
const clearSessionBtn = document.getElementById('clearSessionBtn');

newSessionBtn.addEventListener('click', () => {
    if (confirm('确定创建新会话吗？当前会话将保留在历史记录中。')) {
        createNewSession();
    }
});

clearSessionBtn.addEventListener('click', () => {
    if (confirm('确定清空当前会话的对话历史吗？此操作不可恢复。')) {
        clearCurrentSession();
    }
});

// 页面加载时初始化数字人
window.addEventListener('load', () => {
    console.log('🚀 数字人对话系统已加载');
    console.log('🔑 当前会话 ID:', currentSessionId);
    initAvatar();
});
