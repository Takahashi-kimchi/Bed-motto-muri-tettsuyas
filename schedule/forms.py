# schedule/forms.py

from django import forms
# 【修正】必要なモデルを models.py からインポートする
from .models import Schedule, Course, Task, Day, Period, Timetable

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['name', 'instructor', 'room', 'description', 'color'] # colorを追加
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '授業名'}),
            'instructor': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '担当教員'}),
            'room': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '教室 (例: 302)'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'メモ・備考'}),
            'color': forms.Select(choices=Course.COLOR_CHOICES, attrs={'class': 'form-control'}),
        }
        labels = {
            'name': '授業名',
            'instructor': '担当教員',
            'room': '教室',
            'description': '概要・メモ',
            'color': '授業のテーマカラー',
        }

# 【変更】更新時に room のみ編集するフォームとして ScheduleUpdateForm に名称変更（可読性向上）
# schedule/forms.py

# schedule/forms.py

class ScheduleUpdateForm(forms.ModelForm):
    class Meta:
        model = Schedule
        fields = ['day', 'period']

    def __init__(self, *args, **kwargs):
        self.timetable = kwargs.pop('timetable', None)
        super().__init__(*args, **kwargs)
        if self.timetable:
            self.fields['day'].queryset = Day.objects.filter(timetable=self.timetable).order_by('order')
            self.fields['period'].queryset = Period.objects.filter(timetable=self.timetable).order_by('order')

    def clean(self):
        cleaned_data = super().clean()
        day = cleaned_data.get('day')
        period = cleaned_data.get('period')

        if day and period:
            # 自分自身(現在の授業)を除いて、同じ枠に他の授業がないか探す
            duplicate = Schedule.objects.filter(
                user=self.instance.user,
                day=day,
                period=period
            ).exclude(pk=self.instance.pk).first()

            if duplicate:
                # エラーメッセージを投げる
                raise forms.ValidationError(
                    f"変更できません。{day.name} {period.name} には、すでに「{duplicate.course.name}」が入っています。"
                )
        return cleaned_data

# 【追加】新規作成時に day, period, room を扱うフォーム
class ScheduleCreateForm(forms.ModelForm):
    """時間割スロット（Schedule）情報の新規作成用フォーム（day, period, room を含む）"""
    class Meta:
        model = Schedule
        fields = []

class TaskForm(forms.ModelForm):
    """授業に紐づくタスク（ToDo）のフォーム"""
    class Meta:
        model = Task
        # title, due_date, is_completed を編集できるようにする
        fields = ['title', 'due_date', 'description', 'is_completed']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}), # 日付ピッカーを表示
            'description': forms.Textarea(attrs={'rows': 2}),
        }

class DayForm(forms.ModelForm): # 👈 DayForm の追加
    """曜日（Day）情報のフォーム"""
    class Meta:
        model = Day
        fields = ('name', 'order')
        labels = {
            'name': '曜日名',
            'order': '順序',
        }

class PeriodForm(forms.ModelForm): # 👈 PeriodForm の追加
    """時限（Period）情報のフォーム"""
    class Meta:
        model = Period
        fields = ('name', 'start_time', 'end_time', 'order')
        widgets = {
            # HTML5の Time Input を使用して使いやすくする
            'start_time': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}), 
            'end_time': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),   
        }
        labels = {
            'name': '時限名',
            'start_time': '開始時間',
            'end_time': '終了時間',
            'order': '順序',
        }

# 【追加】TimetableForm
class TimetableForm(forms.ModelForm):
    """時間割セット（Timetable）情報のフォーム"""
    class Meta:
        model = Timetable
        # nameとis_default（デフォルトとして使用するか）を編集可能にする
        fields = ['name', 'is_default']
        labels = {
            'name': '時間割名',
            'is_default': 'デフォルトとして使用',
        }

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class JapaneseSignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("username",)
        labels = {
            'username': 'ユーザー名',
        }
        help_texts = {
            'username': '150文字以内の英数字・記号で入力してください。',
        }