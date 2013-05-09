pyWeiXin_SAElog
===============

this is a python tornado framework based blog system for SAE platform, this blog system can response the request of WeiXin. 

这是一个用python的框架 tornado写的博客系统，这个博客系统带有微信的响应功能，所以能够响应微信用户的请求。

安装教程如下：

配置

修改 /config.yaml 把 name: appname 改为自己的appname，如scnuwriter；
修改 setting.py 的相关设置，每项后面都有说明,包括邮箱，还有数据库密码等。
还有如果不想把自己的博客设为debug状态，可以在index.wsgi文件setting里面，将debug选项改成false。
部署

接下来
到SAE 后台开通相关服务（mysql/Storage/Memcache/Task Queue）
这些服务SAE 是不会自己开通，需要到后台手动完成：
# 1 初始化 Mysql （这是必要的）
# 2 建立一个名为 attachment的 Storage （发帖时上传图片或附件用的）
# 3 启用Memcache，初始化大小为1M 的 mc，大小可以调，日后文章多了，PV多了可酌情增加，让你的博客响应更快。
# 4 创建一个 名为 default 的 Task Queue 这个是用来做发提醒邮件，选择顺序队列 等级 为1
  
打包程序，在SAE 后台通过打包上传代码,注意压缩包下面必须是所有的目录与文件，因为上传展开的是压缩包内的结构；打开 http://your_app_id.sinaapp.com/install 如果出错刷新两三次就可以，提示要输入管理员帐号。

具体请参考博客 http://bibodeng.web-149.com 里面的文章《带微信功能的sae博客》 http://bibodeng.web-149.com/?post=116
