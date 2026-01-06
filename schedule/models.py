# schedule/models.py

from django.db import models
from django.contrib.auth.models import User # Django標準のUserモデルをインポート
from django.core.exceptions import ValidationError

class Timetable(models.Model):
    """ユーザーが管理する時間割のセット（例: '前期時間割', '後期時間割' など）"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, verbose_name="時間割名")
    is_default = models.BooleanField(default=False) # デフォルトとして使用するか
    
    class Meta:
        # ユーザーは同じ名前の時間割を複数持てないようにする
        unique_together = ('user', 'name')

    def __str__(self):
        return f"{self.user.username}'s {self.name}"

# 1. 曜日 (Day) マスタ：柔軟な曜日の変更に対応
class Day(models.Model):
    """曜日または時間割の列"""
    # user フィールドを削除し、timetable に置き換える
    # user = models.ForeignKey(User, on_delete=models.CASCADE) 👈 これを削除
    timetable = models.ForeignKey(Timetable, on_delete=models.CASCADE) # 👈 これを追加
    name = models.CharField(max_length=50)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'pk']
        # timetable 内で name と order が重複しないようにする
        unique_together = ('timetable', 'name'), ('timetable', 'order')

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        # 同じ時間割の中に、同じ順序(order)の曜日が既にないかチェック
        # (ただし、自分自身を編集している場合は除外する)
        existing = Day.objects.filter(
            timetable=self.timetable,
            order=self.order
        ).exclude(pk=self.pk)

        if existing.exists():
            raise ValidationError({'order': 'この順番は既に使用されています。別の番号にしてください。'})

# 2. 時限 (Period) マスタ：柔軟な時限数の変更に対応
class Period(models.Model):
    """時限または時間割の行"""
    timetable = models.ForeignKey(Timetable, on_delete=models.CASCADE) # 👈 これを追加
    name = models.CharField(max_length=50)
    start_time = models.TimeField()
    end_time = models.TimeField()
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'start_time']
        # timetable 内で name と order が重複しないようにする
        unique_together = ('timetable', 'name'), ('timetable', 'order')

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        # 同じ時間割の中に、同じ順序(order)の時限が既にないかチェック
        existing = Period.objects.filter(
            timetable=self.timetable,
            order=self.order
        ).exclude(pk=self.pk)

        if existing.exists():
            raise ValidationError({'order': 'この順番は既に使用されています。別の番号にしてください。'})

# 3. 授業 (Course) 詳細：時間割を構成する授業の情報
class Course(models.Model):
    name = models.CharField(max_length=100, verbose_name="授業名")
    instructor = models.CharField(max_length=100, verbose_name="担当教員")
    description = models.TextField(blank=True, verbose_name="詳細", default="")
    room = models.CharField(max_length=100, blank=True, verbose_name="教室")

    def __str__(self):
        return f"{self.name} ({self.instructor})"
    
    class Meta:
        verbose_name = "授業"
        verbose_name_plural = "授業"

    COLOR_CHOICES = [
    ('#ffa502', 'オレンジ'),     # 鮮やかなオレンジ
    ('#ff4757', 'レッド'),       # 鮮やかな赤
    ('#e2e8f0', 'ライトグレー'),   # デフォルトの淡いグレー
    ('#2ed573', 'グリーン'),     # ネオングリーン系
    ('#1e90ff', 'ブルー'),       # 鮮やかな青
    ('#3742fa', 'インディゴ'),   # 濃い青紫
    ('#5352ed', 'パープル'),     # 明るい紫
    ('#ff6b81', 'ピンク'),       # ホットピンク
    ('#00ced1', 'ターコイズ'),   # 明るい青緑
    ('#2f3542', 'グレー'),       # 濃いグレー
    ('#ffa801', 'アンバー'),     # 鮮やかなアンバー
    ('#ff7f50', 'コーラル'),     # 鮮やかなコーラル
]
    color = models.CharField(max_length=7, choices=COLOR_CHOICES, default='#e2e8f0')

# 4. 時間割 (Schedule) 本体：どの授業が、いつ、どこで行われるか
class Schedule(models.Model):

    # 【追加】この時間割スロットの所有者
    # PROTECT: ユーザーが削除された場合、時間割スロットは保護される
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="ユーザー")

    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name="授業")
    day = models.ForeignKey(Day, on_delete=models.PROTECT, verbose_name="曜日")
    period = models.ForeignKey(Period, on_delete=models.PROTECT, verbose_name="時限")

    def __str__(self):
        return f"{self.course.name} @ {self.day.name} {self.period.name}"
    
    class Meta:
        verbose_name = "時間割"
        verbose_name_plural = "時間割"
        # 同じ曜日、同じ時限、同じ教室で授業が重複しないようにする制約
        unique_together = ('user', 'day', 'period')

# 【追加】ToDo（タスク）モデル
class Task(models.Model):
    # どの授業（Course）に関連するかを紐づける
    # on_delete=models.CASCADE は、授業が削除されたらタスクも削除するという意味
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200, verbose_name="タスク名")
    description = models.TextField(blank=True, null=True, verbose_name="詳細")
    due_date = models.DateField(null=True, blank=True, verbose_name="期限日")
    is_completed = models.BooleanField(default=False, verbose_name="完了")
    
    def __str__(self):
        return f"[{self.course.name}] {self.title}"