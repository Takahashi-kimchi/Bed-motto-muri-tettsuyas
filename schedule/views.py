from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.db import transaction
from django.db.models import Count, Q
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from datetime import time

from .models import Day, Period, Schedule, Course, Task, Timetable
from .forms import (
    ScheduleUpdateForm, CourseForm, TaskForm, 
    DayForm, PeriodForm, TimetableForm, JapaneseSignUpForm
)

# --- 補助関数 ---

def get_back_url(request):
    """セッションから最後に表示していた時間割に戻るURLを生成"""
    last_pk = request.session.get('last_timetable_pk')
    if last_pk:
        return reverse('schedule:time_table_with_pk', kwargs={'timetable_pk': last_pk})
    return reverse('schedule:time_table')

# --- メインビュー (時間割表示) ---

@login_required
def time_table_view(request, timetable_pk=None):
    """メインの時間割画面を表示する"""
    show_all = request.GET.get('all') == '1'
    jst_now = timezone.localtime(timezone.now())
    today = jst_now.date() 
    next_week = today + timezone.timedelta(days=7)

    # 1. 表示する時間割セットの特定
    current_timetable = None
    if timetable_pk:
        current_timetable = get_object_or_404(Timetable, pk=timetable_pk, user=request.user)
    if not current_timetable and 'current_timetable_pk' in request.session:
        session_pk = request.session['current_timetable_pk']
        current_timetable = Timetable.objects.filter(pk=session_pk, user=request.user).first()
    if not current_timetable:
        current_timetable = Timetable.objects.filter(user=request.user, is_default=True).first()
    if not current_timetable:
        current_timetable = Timetable.objects.filter(user=request.user).order_by('pk').first()

    days, periods, schedule_data, upcoming_todos = [], [], {}, []
    total_timetable_tasks = completed_timetable_tasks = 0
    
    if current_timetable:
        # セッションに現在の時間割を記録
        request.session['last_timetable_pk'] = current_timetable.pk
        request.session['current_timetable_pk'] = current_timetable.pk
        
        days = Day.objects.filter(timetable=current_timetable).order_by('order', 'pk')
        periods = Period.objects.filter(timetable=current_timetable).order_by('order', 'pk')
        
        user_schedules = Schedule.objects.filter(
            user=request.user,
            day__timetable=current_timetable,
            period__timetable=current_timetable
        ).select_related('day', 'period', 'course')
        
        # グリッドデータの生成
        for day in days:
            schedule_data[day.pk] = {}
            for period in periods:
                schedule_obj = user_schedules.filter(day=day, period=period).first()
                urgency = None
                display_total = display_completed = 0

                if schedule_obj:
                    task_query = Task.objects.filter(course=schedule_obj.course)
                    incomplete_tasks = task_query.filter(is_completed=False)

                    # 緊急度判定
                    if incomplete_tasks.filter(due_date__lt=today).exists():
                        urgency = 'overdue'
                    elif incomplete_tasks.filter(due_date=today).exists():
                        urgency = 'today'
                    elif incomplete_tasks.filter(due_date__lte=next_week).exists():
                        urgency = 'weekly'

                    if show_all:
                        display_total = task_query.count()
                        display_completed = task_query.filter(is_completed=True).count()
                    else:
                        display_total = incomplete_tasks.count()
                        display_completed = 0

                schedule_data[day.pk][period.pk] = {
                    'schedule': schedule_obj,
                    'task_count': display_total,
                    'completed_count': display_completed,
                    'urgency': urgency,
                }

        # 全体の進捗計算
        course_ids = user_schedules.values_list('course_id', flat=True)
        stats = Task.objects.filter(course_id__in=course_ids).aggregate(
            total=Count('pk'), completed=Count('pk', filter=Q(is_completed=True))
        )
        total_timetable_tasks = stats['total'] or 0
        completed_timetable_tasks = stats['completed'] or 0

        # 下部のToDoリスト
        todo_query = Task.objects.filter(course_id__in=course_ids).distinct().select_related('course')
        if not show_all:
            todo_query = todo_query.filter(is_completed=False)
        upcoming_todos = todo_query.order_by('is_completed', 'due_date', 'pk')

        for task in upcoming_todos:
            task.urgency = None
            if not task.is_completed and task.due_date:
                if task.due_date < today: task.urgency = 'overdue'
                elif task.due_date == today: task.urgency = 'today'
                elif task.due_date <= next_week: task.urgency = 'weekly'

    context = {
        'days': days, 'periods': periods, 'schedule_data': schedule_data,
        'current_timetable': current_timetable, 'show_all': show_all,
        'total_timetable_tasks': total_timetable_tasks,
        'completed_timetable_tasks': completed_timetable_tasks,
        'upcoming_todos': upcoming_todos,
        'user_timetables': Timetable.objects.filter(user=request.user).order_by('pk'),
    }
    return render(request, 'schedule/time_table.html', context)

# --- 授業の登録・詳細・更新・削除 ---

@login_required
@transaction.atomic
def schedule_create_view(request, day_pk, period_pk):
    """新しい授業をコマに登録する"""
    day = get_object_or_404(Day, pk=day_pk, timetable__user=request.user)
    period = get_object_or_404(Period, pk=period_pk, timetable__user=request.user)
    back_url = get_back_url(request)
    
    course_form = CourseForm(request.POST or None)
    existing_course = None
    confirm_reuse = request.POST.get('confirm_reuse') == 'true'

    if request.method == 'POST':
        course_name = request.POST.get('name')
        if course_name:
            existing_course = Course.objects.filter(name=course_name, schedule__user=request.user).distinct().first()

        if existing_course and not confirm_reuse:
            # 重複警告を表示するために何もしない
            pass 
        else:
            if confirm_reuse and existing_course:
                course_obj = existing_course
            elif course_form.is_valid():
                course_obj = course_form.save()
            else:
                return render(request, 'schedule/create.html', locals())

            Schedule.objects.create(user=request.user, day=day, period=period, course=course_obj)
            return redirect(back_url)

    return render(request, 'schedule/create.html', {
        'day': day, 'period': period, 'course_form': course_form, 
        'existing_course': existing_course, 'back_url': back_url
    })

@login_required
def schedule_detail_view(request, pk):
    """授業の詳細とToDoを表示する"""
    schedule_obj = get_object_or_404(Schedule, pk=pk, user=request.user)
    show_all = request.GET.get('all') == '1'

    if request.method == 'POST':
        task_form = TaskForm(request.POST)
        if task_form.is_valid():
            new_task = task_form.save(commit=False)
            new_task.course = schedule_obj.course
            new_task.save()
            return redirect(f"{reverse('schedule:detail', kwargs={'pk': pk})}?all={'1' if show_all else '0'}")
    
    tasks = schedule_obj.course.tasks.all().order_by('is_completed', 'due_date')
    if not show_all:
        tasks = tasks.filter(is_completed=False)

    return render(request, 'schedule/detail.html', {
        'schedule': schedule_obj, 'course': schedule_obj.course,
        'tasks': tasks, 'task_form': TaskForm(), 'show_all': show_all,
        'back_url': get_back_url(request),
    })

@login_required
def schedule_update_view(request, pk):
    """授業情報を更新する"""
    schedule_obj = get_object_or_404(Schedule, pk=pk, user=request.user)
    if request.method == 'POST':
        schedule_form = ScheduleUpdateForm(request.POST, instance=schedule_obj, timetable=schedule_obj.day.timetable)
        course_form = CourseForm(request.POST, instance=schedule_obj.course)
        if schedule_form.is_valid() and course_form.is_valid():
            schedule_form.save()
            course_form.save()
            return redirect('schedule:detail', pk=schedule_obj.pk)
    else:
        schedule_form = ScheduleUpdateForm(instance=schedule_obj, timetable=schedule_obj.day.timetable)
        course_form = CourseForm(instance=schedule_obj.course)

    return render(request, 'schedule/update.html', {
        'schedule_form': schedule_form, 'course_form': course_form, 
        'schedule': schedule_obj, 'back_url': get_back_url(request)
    })

@login_required
def schedule_delete_view(request, pk):
    """特定のコマの登録を削除する"""
    schedule_obj = get_object_or_404(Schedule, pk=pk, user=request.user)
    course_obj = schedule_obj.course
    schedule_obj.delete()
    # どこにも使われていない授業データがあれば削除
    if not Schedule.objects.filter(course=course_obj).exists():
        course_obj.delete()
    return redirect(get_back_url(request))

# --- ユーザー・アカウント管理 ---

class SignUpView(CreateView):
    """新規ユーザー登録"""
    form_class = JapaneseSignUpForm
    success_url = reverse_lazy('login')
    template_name = 'registration/signup.html'

class AccountDeleteView(LoginRequiredMixin, DeleteView):
    """アカウント（退会）削除"""
    template_name = 'registration/account_confirm_delete.html'
    success_url = reverse_lazy('login')
    def get_object(self): return self.request.user
    def post(self, request, *args, **kwargs):
        user = self.get_object()
        logout(request)
        user.delete()
        return redirect(self.success_url)

# --- 共通 Mixin (フィルタリング用) ---

class UserDataMixin:
    def get_queryset(self):
        if self.model == Timetable:
            return super().get_queryset().filter(user=self.request.user)
        return super().get_queryset().filter(timetable__user=self.request.user)

# --- 設定センター (時間割セット/曜日/時限の管理) ---

class TimetableListView(LoginRequiredMixin, UserDataMixin, ListView):
    """作成済みの時間割セットと曜日・時限の一覧"""
    model = Timetable
    template_name = 'schedule/timetable_list.html'
    context_object_name = 'timetables'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for tt in context['timetables']:
            tt.day_list = Day.objects.filter(timetable=tt).order_by('order')
            tt.period_list = Period.objects.filter(timetable=tt).order_by('order')
        context['back_url'] = get_back_url(self.request)
        return context

class TimetableCreateView(LoginRequiredMixin, CreateView):
    model = Timetable
    form_class = TimetableForm
    template_name = 'schedule/timetable_form.html'
    success_url = reverse_lazy('schedule:timetable_list')

    def form_valid(self, form):
        # 1. ユーザーをセットして保存
        form.instance.user = self.request.user
        response = super().form_valid(form)
        
        # 保存された新しい時間割を取得
        new_timetable = self.object

        # 2. 直前の時間割構成を引き継ぐロジック
        # 今作ったもの以外で、このユーザーの一番新しい時間割を探す
        latest_timetable = Timetable.objects.filter(user=self.request.user).exclude(pk=new_timetable.pk).order_by('-pk').first()

        if latest_timetable:
            # 直前の時間割がある場合 -> その曜日と時限構成をコピーする
            for day in latest_timetable.day_set.all():
                Day.objects.create(timetable=new_timetable, name=day.name, order=day.order)
            
            for period in latest_timetable.period_set.all():
                Period.objects.create(
                    timetable=new_timetable, 
                    name=period.name, 
                    order=period.order,
                    start_time=period.start_time,
                    end_time=period.end_time,
                )
        
        else:
            # 直前の時間割がない場合（初めての作成） -> デフォルトを作成
            default_days = ['月', '火', '水', '木', '金', '土']
            default_periods = ['1限', '2限', '3限', '4限', '5限']
            
            for i, name in enumerate(default_days):
                Day.objects.create(timetable=new_timetable, name=name, order=i+1)
            
            default_periods = [
                {'name': '1限', 'start': time(9, 20),  'end': time(11, 00)},
                {'name': '2限', 'start': time(11, 10), 'end': time(12, 50)},
                {'name': '3限', 'start': time(13, 40),  'end': time(15, 20)},
                {'name': '4限', 'start': time(15, 30), 'end': time(17, 10)},
                {'name': '5限', 'start': time(17, 20), 'end': time(19, 00)},
            ]

            for i, p_data in enumerate(default_periods):
                Period.objects.create(
                    timetable=new_timetable, 
                    name=p_data['name'], 
                    order=i+1,
                    start_time=p_data['start'],
                    end_time=p_data['end'],
                )
        return response

class TimetableUpdateView(LoginRequiredMixin, UserDataMixin, UpdateView):
    model = Timetable
    form_class = TimetableForm
    template_name = 'schedule/timetable_form.html'
    success_url = reverse_lazy('schedule:timetable_list')

class TimetableDeleteView(LoginRequiredMixin, UserDataMixin, DeleteView):
    model = Timetable
    template_name = 'schedule/timetable_confirm_delete.html'
    success_url = reverse_lazy('schedule:timetable_list')

class DayCreateView(LoginRequiredMixin, CreateView):
    model = Day
    form_class = DayForm
    template_name = 'schedule/day_form.html'
    success_url = reverse_lazy('schedule:timetable_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # フォームを作る前に、URLに含まれる timetable_pk から時間割を取得してセットしておく
        timetable = get_object_or_404(Timetable, pk=self.kwargs['timetable_pk'])
        kwargs['instance'] = Day(timetable=timetable)
        return kwargs

    def form_valid(self, form):
        form.instance.timetable = get_object_or_404(Timetable, pk=self.kwargs.get('timetable_pk'), user=self.request.user)
        return super().form_valid(form)

class DayUpdateView(LoginRequiredMixin, UserDataMixin, UpdateView):
    model = Day
    form_class = DayForm
    template_name = 'schedule/day_form.html'
    success_url = reverse_lazy('schedule:timetable_list')

class DayDeleteView(LoginRequiredMixin, UserDataMixin, DeleteView):
    model = Day
    template_name = 'schedule/day_confirm_delete.html'
    success_url = reverse_lazy('schedule:timetable_list')

class PeriodCreateView(LoginRequiredMixin, CreateView):
    model = Period
    form_class = PeriodForm
    template_name = 'schedule/period_form.html'
    success_url = reverse_lazy('schedule:timetable_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # フォームを作る前に、URLに含まれる timetable_pk から時間割を取得してセットしておく
        timetable = get_object_or_404(Timetable, pk=self.kwargs['timetable_pk'])
        kwargs['instance'] = Period(timetable=timetable)
        return kwargs

    def form_valid(self, form):
        form.instance.timetable = get_object_or_404(Timetable, pk=self.kwargs.get('timetable_pk'), user=self.request.user)
        return super().form_valid(form)

class PeriodUpdateView(LoginRequiredMixin, UserDataMixin, UpdateView):
    model = Period
    form_class = PeriodForm
    template_name = 'schedule/period_form.html'
    success_url = reverse_lazy('schedule:timetable_list')

class PeriodDeleteView(LoginRequiredMixin, UserDataMixin, DeleteView):
    model = Period
    template_name = 'schedule/period_confirm_delete.html'
    success_url = reverse_lazy('schedule:timetable_list')

# --- その他操作 (タスク切り替えなど) ---

@login_required
def task_toggle_complete(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if not task.course.schedule_set.filter(user=request.user).exists(): raise PermissionDenied
    task.is_completed = not task.is_completed
    task.save()
    return redirect('schedule:detail', pk=task.course.schedule_set.filter(user=request.user).first().pk)

@login_required
def task_delete(request, pk):
    task = get_object_or_404(Task, pk=pk)
    sched_pk = task.course.schedule_set.filter(user=request.user).first().pk
    task.delete()
    return redirect('schedule:detail', pk=sched_pk)

@login_required
def task_edit(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if not task.course.schedule_set.filter(user=request.user).exists(): raise PermissionDenied
    form = TaskForm(request.POST or None, instance=task)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('schedule:detail', pk=task.course.schedule_set.filter(user=request.user).first().pk)
    return render(request, 'schedule/task_edit.html', {'form': form, 'task': task})

@login_required
def switch_timetable_view(request, pk):
    timetable = get_object_or_404(Timetable, pk=pk, user=request.user)
    request.session['current_timetable_pk'] = timetable.pk
    return redirect('schedule:time_table')