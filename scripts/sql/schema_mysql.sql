-- =============================================================================
-- see_self · 个人五年计划管理系统 —— MySQL 建库建表脚本
--
-- 数据库：see_life
-- 表结构以 src/seeself/models.py（SQLAlchemy ORM）与当前线上库为准。
-- 四层模型：five_year_plan（五年计划）→ okr（季度 OKR）→ project（项目）→ todo（待办）
-- 另含规划纲要子表：plan_domain / plan_indicator / plan_risk / plan_special_project，
-- 以及事项子记录表 todo_note、系统设置表 app_setting。
--
-- 可直接在 mysql CLI / Navicat / DataGrip 等工具执行；
-- 也可由 scripts/init_mysql.py 自动读取并执行。
-- 脚本幂等：可重复执行，不会删除已有数据（CREATE IF NOT EXISTS）。
--
-- 说明：
--   1) 统一 InnoDB、utf8mb4 字符集；
--   2) created_at / updated_at 在数据库层给 CURRENT_TIMESTAMP 兜底，
--      ORM 运行时仍以应用层 datetime.now() 显式写入为准，二者不冲突；
--   3) 各表之间【不建外键约束】，数据关联关系由应用层代码维护
--      （service 层显式级联删除、create/update 引用校验）。
-- =============================================================================

-- 1. 创建数据库 ----------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS `see_life`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;

USE `see_life`;

-- 2. 系统设置 ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `app_setting` (
  `key`        varchar(100) NOT NULL,
  `value`      text,
  `updated_at` datetime     NOT NULL DEFAULT (now()),
  PRIMARY KEY (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 3. 五年计划 ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `five_year_plan` (
  `id`                INT          NOT NULL AUTO_INCREMENT COMMENT '主键',
  `name`              VARCHAR(100) NOT NULL                COMMENT '计划名称',
  `start_year`        INT          NOT NULL                COMMENT '起始年份（四位）',
  `end_year`          INT          NOT NULL                COMMENT '结束年份（四位，须大于起始年）',
  `description`       TEXT         NULL                    COMMENT '描述',
  `status`            VARCHAR(20)  NOT NULL DEFAULT 'ACTIVE' COMMENT '状态：ACTIVE/ARCHIVED',
  `created_at`        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `period_start`      DATE         NULL                    COMMENT '纲要周期开始（如 2026-09）',
  `period_end`        DATE         NULL                    COMMENT '纲要周期结束（如 2030-12）',
  `vision_positioning` TEXT        NULL                    COMMENT '定位（5 年后成为谁）',
  `vision_core_goals` JSON         NULL                    COMMENT '核心目标 [str]',
  `vision_bottom_lines` JSON       NULL                    COMMENT '底线约束 [str]',
  `evaluation`        JSON         NULL                    COMMENT '评估机制 {…}',
  `year1_goals`       JSON         NULL                    COMMENT '第一年目标 [str]',
  `year1_period`      VARCHAR(100) NULL                    COMMENT '第一年时间窗口',
  `placeholders`      JSON         NULL                    COMMENT '待补充占位 [str]',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='五年计划';

-- 4. 季度 OKR ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `okr` (
  `id`         INT          NOT NULL AUTO_INCREMENT COMMENT '主键',
  `plan_id`    INT          NULL                    COMMENT '挂靠的五年计划 ID（NULL=独立 OKR）',
  `quarter`    VARCHAR(32)  NOT NULL                COMMENT '季度，如 2026Q3',
  `objective`  VARCHAR(200) NOT NULL                COMMENT 'Objective 目标',
  `kr_note`    TEXT         NULL                    COMMENT '关键结果 KR 备注',
  `created_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `kr_results` JSON         NULL                    COMMENT '关键结果列表 [str]',
  PRIMARY KEY (`id`),
  KEY `idx_okr_plan` (`plan_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='季度 OKR';

-- 5. 规划纲要子表 ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `plan_domain` (
  `id`              INT          NOT NULL AUTO_INCREMENT,
  `plan_id`         INT          NOT NULL                COMMENT '所属五年计划 ID',
  `domain`          VARCHAR(50)  NOT NULL                COMMENT '领域名称',
  `status`          VARCHAR(10)  NOT NULL DEFAULT '重点' COMMENT '重点/非重点',
  `baseline`        TEXT         NULL                    COMMENT '现状基线',
  `five_year_target` TEXT        NULL                    COMMENT '五年目标',
  `year1_tasks`     JSON         NULL                    COMMENT '第一年任务 [str]',
  `sort_order`      INT          NOT NULL DEFAULT 0      COMMENT '排序',
  PRIMARY KEY (`id`),
  KEY `idx_domain_plan` (`plan_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='规划领域';

CREATE TABLE IF NOT EXISTS `plan_indicator` (
  `id`              INT          NOT NULL AUTO_INCREMENT,
  `plan_id`         INT          NOT NULL                COMMENT '所属五年计划 ID',
  `kind`            VARCHAR(10)  NOT NULL                COMMENT 'binding=约束性 / expected=预期性',
  `name`            VARCHAR(200) NOT NULL                COMMENT '指标名称',
  `baseline`        TEXT         NULL                    COMMENT '现状基线',
  `target`          TEXT         NULL                    COMMENT '目标值',
  `check_frequency` VARCHAR(50)  NULL                    COMMENT '约束性：检查频率',
  `measure`         VARCHAR(200) NULL                    COMMENT '预期性：衡量方式',
  `sort_order`      INT          NOT NULL DEFAULT 0      COMMENT '排序',
  PRIMARY KEY (`id`),
  KEY `idx_indicator_plan` (`plan_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='规划指标';

CREATE TABLE IF NOT EXISTS `plan_risk` (
  `id`         INT          NOT NULL AUTO_INCREMENT,
  `plan_id`    INT          NOT NULL                COMMENT '所属五年计划 ID',
  `risk_type`  VARCHAR(20)  NOT NULL                COMMENT '风险类型',
  `trigger`    TEXT         NULL                    COMMENT '触发信号',
  `plan`       TEXT         NULL                    COMMENT '应对预案',
  `reserve`    TEXT         NULL                    COMMENT '预留资源/缓冲',
  `sort_order` INT          NOT NULL DEFAULT 0      COMMENT '排序',
  PRIMARY KEY (`id`),
  KEY `idx_risk_plan` (`plan_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='规划风险';

CREATE TABLE IF NOT EXISTS `plan_special_project` (
  `id`                 INT          NOT NULL AUTO_INCREMENT,
  `plan_id`            INT          NOT NULL                COMMENT '所属五年计划 ID',
  `name`               VARCHAR(200) NOT NULL                COMMENT '专项名称',
  `start`              VARCHAR(50)  NULL                    COMMENT '起止时间（文本，如 2026-09）',
  `end`                VARCHAR(50)  NULL                    COMMENT '结束时间（文本）',
  `effort`             TEXT         NULL                    COMMENT '投入估算',
  `milestones`         JSON         NULL                    COMMENT '里程碑节点 [str]',
  `acceptance_criteria` TEXT        NULL                    COMMENT '验收标准',
  `sort_order`         INT          NOT NULL DEFAULT 0      COMMENT '排序',
  PRIMARY KEY (`id`),
  KEY `idx_special_plan` (`plan_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='规划专项';

-- 6. 项目 ----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `project` (
  `id`          INT          NOT NULL AUTO_INCREMENT COMMENT '主键',
  `okr_id`      INT          NULL                   COMMENT '挂靠的 OKR ID（NULL=独立项目）',
  `name`        VARCHAR(100) NOT NULL               COMMENT '项目名称',
  `description` TEXT         NULL                   COMMENT '描述',
  `created_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_project_okr` (`okr_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='项目';

-- 7. 待办（模块-事项两层：parent_id 自引用；completed_at 是否为空表示完成态）-----
CREATE TABLE IF NOT EXISTS `todo` (
  `id`           INT          NOT NULL AUTO_INCREMENT COMMENT '主键',
  `project_id`   INT          NOT NULL               COMMENT '所属项目 ID',
  `title`        VARCHAR(200) NOT NULL               COMMENT '待办标题',
  `description`  TEXT         NULL                   COMMENT '描述',
  `completed_at` DATETIME     NULL                   COMMENT '完成时间（NULL=未完成，非空=已完成）',
  `created_at`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `parent_id`    INT          NULL                   COMMENT '父事项 ID（NULL=模块，非空=模块下事项）',
  `sort_order`   INT          NOT NULL DEFAULT 0     COMMENT '排序',
  PRIMARY KEY (`id`),
  KEY `idx_todo_project` (`project_id`),
  KEY `idx_todo_completed` (`completed_at`),
  KEY `idx_todo_parent` (`parent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='待办';

-- 8. 事项子记录（完成时的 bullet points）---------------------------------------
CREATE TABLE IF NOT EXISTS `todo_note` (
  `id`         INT      NOT NULL AUTO_INCREMENT,
  `todo_id`    INT      NOT NULL                COMMENT '所属事项 ID',
  `content`    TEXT     NOT NULL                COMMENT '要点内容',
  `sort_order` INT      NOT NULL DEFAULT 0      COMMENT '排序',
  `created_at` DATETIME NOT NULL DEFAULT (now()) COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_note_todo` (`todo_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='事项子记录';

-- 9. 结果校验（手动执行时可查看）----------------------------------------------
-- SELECT TABLE_NAME, TABLE_COMMENT FROM information_schema.TABLES
--   WHERE TABLE_SCHEMA = 'see_life' ORDER BY TABLE_NAME;
