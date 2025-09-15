# 用户须知确认功能 需求文档

## 基本信息

- **需求编号**: REQ-2025-01-16-001
- **创建日期**: 2025-01-16
- **创建人**: 开发团队
- **优先级**: 高
- **预估工期**: 5天
- **状态**: 待开发

## 需求概述

### 背景描述
为了确保用户在使用系统前充分了解相关须知内容，需要开发一个用户须知确认功能模块。该模块允许管理员在后台创建和管理须知内容，用户在H5端查看须知并进行确认操作，同时需要收集用户的手机号和照片信息。

### 功能目标
1. 提供后台管理界面，支持须知内容的创建、编辑、发布和管理
2. 提供H5前端页面，用户可查看须知内容并进行确认
3. 收集用户确认时的手机号和照片信息
4. 提供后台查看和管理用户确认记录的功能
5. 支持数据导出和统计分析

### 用户价值
- **管理员**: 可以灵活管理须知内容，实时查看用户确认情况
- **用户**: 清晰了解相关须知，便捷完成确认操作
- **企业**: 确保合规性，留存用户确认记录

## 功能详细说明

### 核心功能
1. **须知内容管理**: 支持富文本编辑、版本管理、发布控制
2. **用户确认流程**: H5页面展示须知，用户填写信息并确认
3. **数据收集**: 收集手机号、照片、确认时间、IP等信息
4. **记录管理**: 后台查看、搜索、筛选、导出确认记录

### 业务流程
```
管理员创建须知 -> 发布须知 -> 用户访问H5页面 -> 查看须知内容 -> 
填写手机号 -> 上传照片 -> 确认提交 -> 系统记录数据 -> 管理员查看记录
```

### 界面要求
- **后台管理界面**: 基于现有Layui框架，保持界面风格一致
- **前端用户界面**: H5响应式设计，适配移动端和桌面端
- **移动端适配**: 重点优化移动端用户体验

## 技术方案

### 数据库设计
#### 新增表结构
```sql
-- 用户须知表
CREATE TABLE user_notice (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    title VARCHAR(200) NOT NULL COMMENT '须知标题',
    content TEXT NOT NULL COMMENT '须知内容',
    status TINYINT DEFAULT 0 COMMENT '状态：0-草稿，1-已发布，2-已停用',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    create_user INT COMMENT '创建用户ID',
    INDEX idx_status (status),
    INDEX idx_create_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户须知表';

-- 用户确认记录表
CREATE TABLE user_notice_confirm (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    notice_id INT NOT NULL COMMENT '须知ID',
    phone VARCHAR(20) NOT NULL COMMENT '用户手机号',
    photo_path VARCHAR(500) COMMENT '照片存储路径',
    confirm_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '确认时间',
    ip_address VARCHAR(50) COMMENT '用户IP地址',
    user_agent TEXT COMMENT '用户代理信息',
    INDEX idx_notice_id (notice_id),
    INDEX idx_phone (phone),
    INDEX idx_confirm_time (confirm_time),
    FOREIGN KEY (notice_id) REFERENCES user_notice(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户确认记录表';
```

### API接口设计
#### 后台管理接口
- `GET /system/notice/main` - 须知列表页面
- `GET /system/notice/data` - 须知列表数据
- `GET /system/notice/add` - 新增须知页面
- `POST /system/notice/save` - 保存须知
- `GET /system/notice/edit/<id>` - 编辑须知页面
- `POST /system/notice/update` - 更新须知
- `POST /system/notice/remove` - 删除须知
- `GET /system/notice/confirm/main` - 确认记录列表页面
- `GET /system/notice/confirm/data` - 确认记录列表数据
- `GET /system/notice/confirm/export` - 导出确认记录

#### 前端用户接口
- `GET /h5/notice/<id>` - 获取须知详情页面
- `GET /api/notice/<id>` - 获取须知内容数据
- `POST /api/notice/confirm` - 提交确认信息
- `POST /api/upload/photo` - 上传照片

### 文件存储方案
- **存储路径**: uploads/notice_photos/YYYY/MM/DD/
- **文件命名**: {timestamp}_{random_string}.{ext}
- **支持格式**: JPG、PNG、JPEG
- **大小限制**: 单张照片最大5MB
- **图片处理**: 自动压缩，生成缩略图

## 安全考虑

- **权限控制**: 使用现有@authorize装饰器进行权限验证
- **数据验证**: 手机号格式验证，文件类型和大小验证
- **文件安全**: 文件类型检查，路径安全，防止上传恶意文件
- **防护措施**: CSRF防护、XSS防护、SQL注入防护

## 性能要求

- **响应时间**: 页面加载时间 < 3秒
- **并发处理**: 支持100个并发用户
- **数据量**: 支持10万条确认记录
- **文件处理**: 图片上传和压缩 < 5秒

## 兼容性要求

- **浏览器兼容**: Chrome 60+, Safari 12+, Firefox 60+
- **移动端兼容**: iOS 12+, Android 8+
- **系统兼容**: Windows, macOS, Linux

## 测试要求

### 功能测试
- [ ] 须知管理功能测试
- [ ] 用户确认流程测试
- [ ] 文件上传功能测试
- [ ] 数据导出功能测试
- [ ] 边界条件测试
- [ ] 异常情况测试

### 性能测试
- [ ] 页面加载性能测试
- [ ] 并发用户压力测试
- [ ] 大数据量查询测试
- [ ] 文件上传性能测试

### 安全测试
- [ ] 权限控制测试
- [ ] 数据安全测试
- [ ] 文件上传安全测试
- [ ] SQL注入防护测试
- [ ] XSS攻击防护测试

## 验收标准

### 功能验收
1. 管理员可以创建、编辑、发布、删除须知内容
2. 用户可以在H5页面查看须知并完成确认操作
3. 系统正确收集用户手机号和照片信息
4. 管理员可以查看、搜索、导出确认记录
5. 所有表单验证和错误提示正常工作

### 性能验收
1. 页面加载时间符合要求
2. 支持指定并发用户数
3. 大数据量查询响应时间合理
4. 文件上传处理时间符合要求

### 安全验收
1. 权限控制有效，未授权用户无法访问管理功能
2. 数据验证完整，防止恶意数据提交
3. 文件上传安全，防止恶意文件上传
4. 防护措施有效，抵御常见攻击

## 风险评估

### 技术风险
- **风险点**: 文件上传和处理可能影响服务器性能
- **影响程度**: 中
- **应对措施**: 实施文件大小限制、异步处理、定期清理

### 进度风险
- **风险点**: H5页面兼容性调试可能耗时较长
- **影响程度**: 中
- **应对措施**: 提前进行兼容性测试，预留调试时间

## 后续规划

- **版本迭代**: v2.0考虑增加电子签名功能
- **功能扩展**: 支持多媒体须知内容（视频、音频）
- **优化方向**: 提升移动端用户体验，增加数据分析功能

## 附录

### 参考资料
- Flask官方文档
- SQLAlchemy文档
- Layui组件库文档

### 变更记录
| 日期 | 版本 | 变更内容 | 变更人 |
|------|------|----------|--------|
| 2025-01-16 | v1.0 | 初始版本 | 开发团队 |