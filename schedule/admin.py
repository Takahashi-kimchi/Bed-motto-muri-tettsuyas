# schedule/admin.py

from django.contrib import admin
from .models import Timetable, Day, Period, Course, Schedule, Task

# モデルを管理画面に登録
admin.site.register(Day)
admin.site.register(Period)
admin.site.register(Course)
admin.site.register(Schedule)

# 【追加】Taskモデルを管理画面に登録
admin.site.register(Task)

@admin.register(Timetable)
class TimetableAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'is_default')
    # 必要に応じてカスタマイズ
    pass