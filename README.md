# 時間割管理アプリ

**Group Name:** ベッド・モット・ムリ・テッツヤーズ

**Group Member:** 髙橋響(2442051)、西村優輝(2442064)、本間央樹(2442076)、横井仁(2442091)

> **App URL:** https://timetable-y91y.onrender.com/
> 
> **Note:** 無料プランのサーバー(Render Free Tier)を使用しているため、
> **起動に約1分かかることがありますが、エラーではありませんのでご安心ください。**

---

## 🎥 1. Demonstration
実際のアプリの動作デモ動画です。

**Demo Video URL:**
[リンク: ここにYouTubeまたはGoogleDriveの共有リンクを貼ってください]

> **動画の内容:**
> 1. ユーザーログイン
> 2. 新しい時間割の作成
> 3. 授業の登録（曜日・時限の選択）
> 4. エラーハンドリング（重複登録時の警告）の確認

---

## 🗓 2. Project Management (PM)
GitHub Projects (Kanban Board) を活用し、タスクの可視化と進捗管理を行いました。

**Kanban Board Snapshot:**
[![Kanban Board]([画像: ここにGitHub Projectsのカンバンボードのスクショ画像を貼ってください])]
(https://github.com/users/Takahashi-kimchi/projects/1/views/1?layout_template=boa)

---

## 👤 3. User Analysis (Business Analyst)

### Target Persona (ペルソナ)
* **名前:**
髙橋響
* **職業:**
大学二年生
* **概要:**
大学生活に慣れてきたが、バイトとの両立に苦しんでおり、操作性の高い時間割アプリを使いたいと思っている。今までいくつかの時間割アプリを使ってきたが、拡張性の低さに苦しんでいる。
* **システムへの要件:**
時限、曜日を自由に変えられる、時限や曜日の部分は自由記述にすることで講義以外の予定の管理もできるとよい。ToDoリストは実装してほしい。授業ごとのToDoリストの進捗度もわかるとうれしい。

### Story Board (利用シナリオ)
ユーザーが課題を解決するまでのストーリー：

![Story Board]([画像: ここにストーリーボード（4コマ漫画や図）の画像を貼ってください])

1. **Scene 1 (課題発生):** [記述: 朝、寝坊して教室がわからない！ポータルも繋がらない！]
2. **Scene 2 (解決策):** [記述: Timetable SaaSを開く。0.5秒で時間割が表示される。]
3. **Scene 3 (価値享受):** [記述: 「あ、3号館か」と即座に理解し、遅刻を回避。]

---

## 🏗 4. System Architecture (Architect)
クラウドネイティブな **Web 3層構造 (Web 3 Layer Architecture)** を採用しました。

### Architecture Diagram

```mermaid
%%{init: {'theme': 'neutral'} }%%
graph LR
    User(("User<br/>(PC / Mobile)"))
    DNS{"DNS<br/>onrender.com"}
    
    subgraph "Application Server (Render)"
        LB["Load Balancer<br/>(Render Proxy)"]
        Gunicorn["WSGI Server<br/>(Gunicorn)"]
        Django["Web App<br/>(Django Framework)"]
        Static["Static Files<br/>(WhiteNoise)"]
    end
    
    subgraph "Database Server (Neon)"
        DB[("RDBMS<br/>PostgreSQL")]
    end

    %% データの流れ
    User -- HTTPS Request --> DNS
    DNS --> LB
    LB --> Gunicorn
    Gunicorn --> Django
    
    Django -- SQL Query --> DB
    DB -- Result Data --> Django
    
    Django -- Read CSS/JS --> Static
    Django -- HTML Response --> User

    %% スタイル定義
    style User fill:#f9f,stroke:#333
    style Django fill:#bbf,stroke:#333
    style DB fill:#bfb,stroke:#333

```

### Non-Functional Requirements (非機能要件の定義)
* **RPO (Recovery Point Objective):** 24時間
    * Neon DatabaseのPITR (Point-in-Time Recovery) 機能に準拠。
* **RTO (Recovery Time Objective):** 1時間以内
    * GitHub ActionsによるCI/CDパイプラインと、IaC (Infrastructure as Code) 的な構成により迅速な復旧が可能。
* **Performance Strategy:**
    * **WhiteNoise** を導入し、Webサーバー単体で静的ファイル（CSS/JS）を高速配信。
    * **Gunicorn** を用いた並列処理によるレスポンス最適化。

---

## 🗃 5. Database Design (DBA)
データの整合性を最優先し、リレーショナルデータベース (PostgreSQL) を採用しました。

### ER Diagram
```mermaid
%%{init: {'theme': 'neutral'} }%%
erDiagram
    User ||--o{ Timetable : "所有する"
    User ||--o{ Schedule : "登録する"
    Timetable ||--|{ Day : "構成要素"
    Timetable ||--|{ Period : "構成要素"
    
    Day ||--o{ Schedule : "割り当て"
    Period ||--o{ Schedule : "割り当て"
    
    Course ||--o{ Schedule : "授業インスタンス"
    Course ||--o{ Task : "課題を持つ"

    User {
        int id PK
        string username
    }

    Timetable {
        int id PK
        int user_id FK
        string name "時間割名"
        boolean is_default "メインフラグ"
    }

    Day {
        int id PK
        int timetable_id FK
        string name "曜日名"
        int order "表示順"
    }

    Period {
        int id PK
        int timetable_id FK
        string name "時限名"
        time start_time
        time end_time
        int order "表示順"
    }

    Course {
        int id PK
        string name "授業名"
        string instructor "担当教員"
        string room "教室"
        string color "テーマカラー"
    }

    Schedule {
        int id PK
        int user_id FK
        int course_id FK
        int day_id FK
        int period_id FK
    }

    Task {
        int id PK
        int course_id FK
        string title "タスク名"
        date due_date "期限"
        boolean is_completed "完了フラグ"
    }
```

### Key Database Features (評価ポイント)

* **高度な正規化とデータ整合性 (Normalization):**
    * 単なる時間割の記録に留まらず、`Course`（授業情報）と`Schedule`（配置情報）を分離。これにより、週2回ある同一科目が**課題（Task）やメモを自動的に共有**できる設計となっており、データの重複を排除しつつ実用性を高めています。
* **複合ユニーク制約による衝突防止 (Unique Constraints):**
    * データベースレベルで `unique_together = ('user', 'day', 'period')` を設定。物理的なデータの重複登録を未然に防ぐとともに、アプリケーション層での論理チェック（重複警告UI）と組み合わせた多重のガードを構築しています。
* **戦略的な参照整合性 (Foreign Key Strategy):**
    * `CASCADE`（時間割削除時に曜日・時限を連動削除）と `PROTECT`（授業配置がある曜日・時限の不用意な削除を防止）を使い分け。ユーザーの誤操作によるデータ消失を防ぎ、リレーショナルデータベースとしての整合性を維持しています。
* **トランザクションの原子性 (Atomic Transactions):**
    * `@transaction.atomic` を採用。授業の新規登録時、既存データの有無をチェックし「再利用」または「新規作成」を行う一連のプロセスを一つの単位として処理。エラー時の自動ロールバックにより、中途半端なデータ書き込みを許しません。

---

## 💻 6. Technical Stack & Process
このアプリケーションは以下の技術スタックで構築されています。

| Layer | Technology | Description |
| :--- | :--- | :--- |
| **Frontend** | HTML5, Bootstrap 5 | レスポンシブデザイン対応 (Mobile First) |
| **Backend** | Python 3.12, Django 5.0 | MVTアーキテクチャ, バリデーションロジック |
| **Database** | PostgreSQL (Neon) | Serverless SQL Database |
| **Infrastructure** | Render | PaaS (Platform as a Service) |
| **Version Control** | Git / GitHub | ソースコード管理 |

### Application Process Flow
1. **Request:** ユーザーがHTTPSリクエストを送信。
2. **Routing:** Djangoの `urls.py` がリクエストを解析し、適切なViewに振り分け。
3. **Logic:** `views.py` がDBからデータを取得し、重複チェック等のビジネスロジックを実行。
4. **Response:** データを埋め込んだHTMLテンプレートをレンダリングして返却。
