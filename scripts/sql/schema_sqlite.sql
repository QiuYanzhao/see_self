-- =============================================================================
-- see_self · 个人五年计划管理系统 —— SQLite 建表脚本（本地开发/测试对照用）
--
-- 与 src/seeself/models.py 保持一致；生产使用 MySQL，见同目录 schema_mysql.sql。
-- 各表之间【不建外键约束】，数据关联关系由应用层代码维护
-- （service 层显式级联删除、create/update 引用校验）。
--
-- 用法：sqlite3 data/seeself.db < scripts/sql/schema_sqlite.sql
-- 幂等：DROP（逆序）后重建，注意会清空已有数据。
-- =============================================================================

PRAGMA foreign_keys = OFF;

DROP TABLE IF EXISTS `todo_note`;
DROP TABLE IF EXISTS `todo`;
DROP TABLE IF EXISTS `project`;
DROP TABLE IF EXISTS `plan_special_project`;
DROP TABLE IF EXISTS `plan_risk`;
DROP TABLE IF EXISTS `plan_indicator`;
DROP TABLE IF EXISTS `plan_domain`;
DROP TABLE IF EXISTS `okr`;
DROP TABLE IF EXISTS `five_year_plan`;
DROP TABLE IF EXISTS `app_setting`;

PRAGMA foreign_keys = ON;

-- 系统设置
CREATE TABLE `app_setting` (
  `key`        VARCHAR(100) NOT NULL PRIMARY KEY,
  `value`      TEXT,
  `updated_at` DATETIME     NOT NULL
);

-- 五年计划
CREATE TABLE `five_year_plan` (
  `id`                 INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
  `name`               VARCHAR(100) NOT NULL,
  `start_year`         INTEGER      NOT NULL,
  `end_year`           INTEGER      NOT NULL,
  `description`        TEXT,
  `status`             VARCHAR(20)  NOT NULL DEFAULT 'ACTIVE',
  `created_at`         DATETIME     NOT NULL,
  `updated_at`         DATETIME     NOT NULL,
  `period_start`       DATE,
  `period_end`         DATE,
  `vision_positioning` TEXT,
  `vision_core_goals`  TEXT,
  `vision_bottom_lines` TEXT,
  `evaluation`         TEXT,
  `year1_goals`        TEXT,
  `year1_period`       VARCHAR(100),
  `placeholders`       TEXT
);

-- 季度 OKR
CREATE TABLE `okr` (
  `id`         INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
  `plan_id`    INTEGER,
  `quarter`    VARCHAR(32)  NOT NULL,
  `objective`  VARCHAR(200) NOT NULL,
  `kr_note`    TEXT,
  `created_at` DATETIME     NOT NULL,
  `updated_at` DATETIME     NOT NULL,
  `kr_results` TEXT
);
CREATE INDEX `idx_okr_plan` ON `okr` (`plan_id`);

-- 规划纲要子表
CREATE TABLE `plan_domain` (
  `id`               INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
  `plan_id`          INTEGER      NOT NULL,
  `domain`           VARCHAR(50)  NOT NULL,
  `status`           VARCHAR(10)  NOT NULL DEFAULT '重点',
  `baseline`         TEXT,
  `five_year_target` TEXT,
  `year1_tasks`      TEXT,
  `sort_order`       INTEGER      NOT NULL DEFAULT 0
);
CREATE INDEX `idx_domain_plan` ON `plan_domain` (`plan_id`);

CREATE TABLE `plan_indicator` (
  `id`              INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
  `plan_id`         INTEGER      NOT NULL,
  `kind`            VARCHAR(10)  NOT NULL,
  `name`            VARCHAR(200) NOT NULL,
  `baseline`        TEXT,
  `target`          TEXT,
  `check_frequency` VARCHAR(50),
  `measure`         VARCHAR(200),
  `sort_order`      INTEGER      NOT NULL DEFAULT 0
);
CREATE INDEX `idx_indicator_plan` ON `plan_indicator` (`plan_id`);

CREATE TABLE `plan_risk` (
  `id`         INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
  `plan_id`    INTEGER      NOT NULL,
  `risk_type`  VARCHAR(20)  NOT NULL,
  `trigger`    TEXT,
  `plan`       TEXT,
  `reserve`    TEXT,
  `sort_order` INTEGER      NOT NULL DEFAULT 0
);
CREATE INDEX `idx_risk_plan` ON `plan_risk` (`plan_id`);

CREATE TABLE `plan_special_project` (
  `id`                 INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
  `plan_id`            INTEGER      NOT NULL,
  `name`               VARCHAR(200) NOT NULL,
  `start`              VARCHAR(50),
  `end`                VARCHAR(50),
  `effort`             TEXT,
  `milestones`         TEXT,
  `acceptance_criteria` TEXT,
  `sort_order`         INTEGER      NOT NULL DEFAULT 0
);
CREATE INDEX `idx_special_plan` ON `plan_special_project` (`plan_id`);

-- 项目
CREATE TABLE `project` (
  `id`          INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
  `okr_id`      INTEGER,
  `name`        VARCHAR(100) NOT NULL,
  `description` TEXT,
  `created_at`  DATETIME     NOT NULL,
  `updated_at`  DATETIME     NOT NULL
);
CREATE INDEX `idx_project_okr` ON `project` (`okr_id`);

-- 待办（模块-事项两层：parent_id 自引用）
CREATE TABLE `todo` (
  `id`           INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
  `project_id`   INTEGER      NOT NULL,
  `title`        VARCHAR(200) NOT NULL,
  `description`  TEXT,
  `completed_at` DATETIME,
  `created_at`   DATETIME     NOT NULL,
  `updated_at`   DATETIME     NOT NULL,
  `parent_id`    INTEGER,
  `sort_order`   INTEGER      NOT NULL DEFAULT 0
);
CREATE INDEX `idx_todo_project` ON `todo` (`project_id`);
CREATE INDEX `idx_todo_completed` ON `todo` (`completed_at`);
CREATE INDEX `idx_todo_parent` ON `todo` (`parent_id`);

-- 事项子记录
CREATE TABLE `todo_note` (
  `id`         INTEGER  NOT NULL PRIMARY KEY AUTOINCREMENT,
  `todo_id`    INTEGER  NOT NULL,
  `content`    TEXT     NOT NULL,
  `sort_order` INTEGER  NOT NULL DEFAULT 0,
  `created_at` DATETIME NOT NULL
);
CREATE INDEX `idx_note_todo` ON `todo_note` (`todo_id`);
