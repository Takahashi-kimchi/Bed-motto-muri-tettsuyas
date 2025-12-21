from django.urls import path
from . import views

app_name = 'schedule'

urlpatterns = [
    # 時間割表示
    path('', views.time_table_view, name='time_table'),
    path('<int:timetable_pk>/', views.time_table_view, name='time_table_with_pk'),
    path('switch/<int:pk>/', views.switch_timetable_view, name='switch_timetable'),

    # 授業（Schedule/Course）操作
    path('create/<int:day_pk>/<int:period_pk>/', views.schedule_create_view, name='create'),
    path('detail/<int:pk>/', views.schedule_detail_view, name='detail'),
    path('update/<int:pk>/', views.schedule_update_view, name='update'),
    path('delete/<int:pk>/', views.schedule_delete_view, name='delete'), # views.pyの関数名に合わせました

    # ToDo（Task）操作
    path('task/<int:pk>/toggle/', views.task_toggle_complete, name='task_toggle'),
    path('task/<int:pk>/edit/', views.task_edit, name='task_edit'),
    path('task/<int:pk>/delete/', views.task_delete, name='task_delete'),

    # 設定センター（時間割セット管理）
    path('timetables/', views.TimetableListView.as_view(), name='timetable_list'),
    path('timetables/add/', views.TimetableCreateView.as_view(), name='timetable_create'),
    path('timetables/<int:pk>/edit/', views.TimetableUpdateView.as_view(), name='timetable_update'),
    path('timetables/<int:pk>/delete/', views.TimetableDeleteView.as_view(), name='timetable_delete'),

    # 曜日管理
    path('timetables/<int:timetable_pk>/days/add/', views.DayCreateView.as_view(), name='day_create'),
    path('days/<int:pk>/edit/', views.DayUpdateView.as_view(), name='day_update'),
    path('days/<int:pk>/delete/', views.DayDeleteView.as_view(), name='day_delete'),

    # 時限管理
    path('timetables/<int:timetable_pk>/periods/add/', views.PeriodCreateView.as_view(), name='period_create'),
    path('periods/<int:pk>/edit/', views.PeriodUpdateView.as_view(), name='period_update'),
    path('periods/<int:pk>/delete/', views.PeriodDeleteView.as_view(), name='period_delete'),

    # アカウント管理
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('account/delete/', views.AccountDeleteView.as_view(), name='account_delete'),
]