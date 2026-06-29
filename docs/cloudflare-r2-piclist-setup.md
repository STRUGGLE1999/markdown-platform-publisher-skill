## 一、为什么选 </font>Cloudflare </font>R2 + PicList</font>
用过图床的人多少都踩过坑：七牛、又拍的免费额度越缩越小，阿里云 OSS 的下行流量按 GB 收费让人提心吊胆，GitHub 图床在国内访问全靠缘分。</font>

Cloudflare R2 的出现基本终结了这些烦恼。它基于 S3 协议，但</font>**下行流量完全免费</font>**——这是和其他对象存储最大的区别。搭配 PicList 客户端，原生支持 R2，不用装插件，还自带 WebP 转换和云端相册管理。</font>

简单对比一下主流方案的费用：</font>

  
<!-- 这是一张图片，ocr 内容为： -->
![1782716289564-dddfb65e-a412-4137-9bc4-b75940f13e64.png](https://pub-51f65a9eade44d299ca17b0d6dd95654.r2.dev/articles/codex/1782716289564-dddfb65e-a412-4137-9bc4-b75940f13e64.png)

对于个人博客、笔记配图这种量级，R2 的免费额度基本用不完。</font>

## 二、Cloudflare R2 配置</font>
登录Cloudflare之后可以点击右上角选择中文语言界面，如下图所示。</font>

<!-- 这是一张图片，ocr 内容为： -->
![1782716641943-1eba68f1-7153-4ee7-8ec5-db9051ea2e07.png](https://pub-51f65a9eade44d299ca17b0d6dd95654.r2.dev/articles/codex/1782716641943-1eba68f1-7153-4ee7-8ec5-db9051ea2e07.png)  
</font>2.1 创建 Bucket + 生成 API Token</font>

登录 </font>[Cloudflare Dashboard</font>](https://dash.cloudflare.com/)，进入左侧 </font>**存储和数据库-R2对象存储</font>**，点击 </font>**创建存储桶</font>**。创建桶之前需要添加一个R2订阅，可以添加一张银行卡，国内的也行。</font>

<!-- 这是一张图片，ocr 内容为： -->
![1782640222959-80144f35-72ff-4bff-8b12-2f0d4a88facb.png](https://pub-51f65a9eade44d299ca17b0d6dd95654.r2.dev/articles/codex/1782640222959-80144f35-72ff-4bff-8b12-2f0d4a88facb.png)

<!-- 这是一张图片，ocr 内容为： -->
![1782716767158-f868f587-78ce-4f5c-94d1-e6b8931a9fc4.png](https://pub-51f65a9eade44d299ca17b0d6dd95654.r2.dev/articles/codex/1782716767158-f868f587-78ce-4f5c-94d1-e6b8931a9fc4.png)

存储桶名称 命名建议简洁有意义，比如 img 或 blog-images。</font>

<!-- 这是一张图片，ocr 内容为： -->
![1782716913930-75a000f0-6813-40ad-ac66-539f19d359f9.png](https://pub-51f65a9eade44d299ca17b0d6dd95654.r2.dev/articles/codex/1782716913930-75a000f0-6813-40ad-ac66-539f19d359f9.png)

创建完成后，进入 </font>**R2 概览页 → 管理 → Create API Token</font>**，权限选择 </font>**Object Read & Write</font>**，作用范围可以限定到刚才创建的 Bucket。</font>

<!-- 这是一张图片，ocr 内容为： -->
![1782717189422-2e1ea62b-d168-405c-b5a8-db8f7ebebb5f.png](https://pub-51f65a9eade44d299ca17b0d6dd95654.r2.dev/articles/codex/1782717189422-2e1ea62b-d168-405c-b5a8-db8f7ebebb5f.png)

<!-- 这是一张图片，ocr 内容为： -->
![1782717257887-edea61a3-ab64-4979-8b4d-95a24af3350d.png](https://pub-51f65a9eade44d299ca17b0d6dd95654.r2.dev/articles/codex/1782717257887-edea61a3-ab64-4979-8b4d-95a24af3350d.png)

<!-- 这是一张图片，ocr 内容为： -->
![1782717330190-c6bce6b7-45c7-4f66-9f33-972be3cd445f.png](https://pub-51f65a9eade44d299ca17b0d6dd95654.r2.dev/articles/codex/1782717330190-c6bce6b7-45c7-4f66-9f33-972be3cd445f.png)

创建成功后会显示三个关键值，务必保存好：</font>

+ **Access Key ID(访问密钥ID)</font>**
+ **Secret Access Key(机密访问密钥)</font>**
+ **Endpoint URL</font>**（格式类似 https://<account_id>.r2.cloudflarestorage.com）（终结点）</font>

<!-- 这是一张图片，ocr 内容为： -->
![1782717552722-dfdc9ba1-2ee6-4808-8a05-75a20587c5a2.png](https://pub-51f65a9eade44d299ca17b0d6dd95654.r2.dev/articles/codex/1782717552722-dfdc9ba1-2ee6-4808-8a05-75a20587c5a2.png)

</font> Secret Access Key 只显示一次，关掉就看不到了。建议立刻保存好</font>



## 三、PicList 客户端配置</font>
3.1 连接 R2</font>

到 </font>[PicList GitHub Releases</font>](https://github.com/Kuingsmile/PicList/releases)下载最新版本安装。</font>

打开 PicList，进入 </font>**图床设置</font>**，选择 </font>**Amazon S3</font>**（R2 兼容 S3 协议）。填入以下信息：</font>

<!-- 这是一张图片，ocr 内容为： -->
![1782720256565-5f05ab2c-b77b-41c6-9b01-c099077968f1.png](https://pub-51f65a9eade44d299ca17b0d6dd95654.r2.dev/articles/codex/1782720256565-5f05ab2c-b77b-41c6-9b01-c099077968f1.png)



<!-- 这是一张图片，ocr 内容为： -->
![1782720825094-aa29bfba-6170-48c3-8ebf-371cd9f5a4d4.png](https://pub-51f65a9eade44d299ca17b0d6dd95654.r2.dev/articles/codex/1782720825094-aa29bfba-6170-48c3-8ebf-371cd9f5a4d4.png)

<!-- 这是一张图片，ocr 内容为： -->
![1782720978973-a36f038d-e9d2-4518-b33d-32f55e72b010.png](https://pub-51f65a9eade44d299ca17b0d6dd95654.r2.dev/articles/codex/1782720978973-a36f038d-e9d2-4518-b33d-32f55e72b010.png)

存储路径模板用 {year}/{month} 按月归档，{md5} 作为文件名避免重名，整理起来会很清晰。</font>

填好后点击 </font>**确认</font>** 并 </font>**设为默认图床</font>**，随便上传一张图测试，能拿到链接就说明配置成功。</font>





