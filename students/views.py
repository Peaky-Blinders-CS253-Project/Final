# students/views.py
from django.shortcuts import render, redirect
from django.views import View
from .models import Student, BaseMealPrecancellation, BookingExtraItems
from .forms import StudentCardForm
from .forms import StudentLoginForm
from django.contrib.auth import authenticate, login, logout
from .forms import StudentRegistrationForm
from django.contrib.auth.forms import AuthenticationForm
from django.views.generic import FormView
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password
from .models import ExtraItem, BreakdownChartExtra, BreakdownChart
from django.views.generic import View
from django.shortcuts import render
from django.http import HttpResponseForbidden
from django.utils import timezone
from django.views.generic import ListView, DetailView
from datetime import date
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.views.generic import FormView
from .forms import StudentLoginForm
from django.urls import reverse_lazy

class ExtraItemListView(ListView):
    model = ExtraItem
    template_name = 'students/extra_item_list.html'
    context_object_name = 'extra_items'

class ExtraItemDetailView(DetailView):
    model = ExtraItem
    template_name = 'extra_item_detail.html'
    context_object_name = 'extra_item'

from django.http import HttpResponseBadRequest

@login_required
def book_extra_item(request, pk):
    extra_item = ExtraItem.objects.get(pk=pk)
    student = Student.objects.get(username=request.user.username)  # Assuming you have a OneToOneField linking Student to User
    quantity = int(request.POST['quantity'])
    price = extra_item.price * quantity

    # Set the default base meal price (replace this with your actual logic)
    base_meal_price = 0.00  # Example base meal price

    # Create or update the breakdown chart for the student
    breakdown_chart, _ = BreakdownChart.objects.get_or_create(student=student, date=date.today())
    breakdown_chart.base_meal_price = base_meal_price  # Set the base meal price
    breakdown_chart.save()

    # Create or update the breakdown chart extra for the student
    breakdown_chart_extra, _ = BreakdownChartExtra.objects.get_or_create(breakdown_chart=breakdown_chart, extra_item=extra_item)
    breakdown_chart_extra.quantity += quantity
    breakdown_chart_extra.price += price
    breakdown_chart_extra.save()

    # Update the total extras price and total cost in the breakdown chart
    breakdown_chart.total_extras_price += price
    breakdown_chart.total_cost += price
    breakdown_chart.save()

    return redirect('booking_success')

def booking_success(request):
    return render(request, 'students/extrabook_success.html')



def student_breakdown_view(request):
    student = request.user  # Assuming you have a OneToOneField linking Student to User
    breakdowns = BreakdownChart.objects.filter(student=student)
    breakdown_extras = BreakdownChartExtra.objects.filter(breakdown_chart__student=student)

    return render(request, 'students/student_breakdown.html', {'breakdowns': breakdowns, 'breakdown_extras': breakdown_extras})





class StudentdashboardView(View):
    
    def get(self, request, rollno, *args, **kwargs):
        if request.user.is_student and request.user.rollno == rollno:
            return render(request, 'students/student_dashboard.html', {'rollno': rollno})
        else:
            return HttpResponseForbidden("You are not authorized to access this page.")
        
        # Check if the roll number in the URL matches the logged-in user's roll number
        #if str(request.user.rollno) != rollno:
        #   return HttpResponseForbidden("")
        
        # Your view logic here
        if not request.user.is_student and request.user.rollno != rollno and request.user.rollno == 0 :
            return HttpResponseForbidden("You are not authorized to access this page.")



class StudentRegisterView(FormView):
    template_name = 'students/student_register.html'
    form_class = StudentRegistrationForm

    def form_valid(self, form):
        # Extract username and password from the form
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        
        try:
            # Get the student instance from the database
            student = Student.objects.get(username=username)
            # Update the password for the existing user
            student.password = make_password(password)
            # Save the updated student object
            student.save()
            # Authenticate and login the user
            user = authenticate(username=username, password=password)
            if user is not None:
                login(self.request, user)
                return HttpResponseRedirect(self.get_success_url())
        except Student.DoesNotExist:
            pass  # Username does not exist, let the form handle the validation error
        
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('student_dashboard')

from django.contrib import messages

class StudentLoginView(FormView):
    template_name = 'students/student_login.html'
    form_class = StudentLoginForm

    def form_valid(self, form):
        roll_no = form.cleaned_data['roll_no']
        password = form.cleaned_data['password']

        # Authenticate only if the user is a student
        user = authenticate(rollno=roll_no, password=password)
        if user is not None:
            if user.is_student:
                login(self.request, user)
                success_url = reverse_lazy('student_dashboard', kwargs={'rollno': user.rollno})
                return redirect(success_url)
            else:
                messages.error(self.request, 'You are not authorized to access this page.')
        else:
            messages.error(self.request, 'Invalid username or password')
        return self.form_invalid(form)











class StudentLogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('student_login')  # Redirect to student login page
        
import datetime
from django.http import JsonResponse

def base_meal_precancellations(request,rollno):
    return render(request, 'students/base_meal_precancellation.html')


def meal_cancel(request,rollno):
    if not request.user.is_student and request.user.rollno != rollno and request.user.rollno == 0 :
            return HttpResponseForbidden("You are not authorized to access this page.")
    if request.user.is_student and request.user.rollno == rollno:
        context = {'rollno': rollno}
        if request.method == 'POST':
            cancel_date = request.POST.get('canceldate')
            cancel_time = request.POST.get('canceltime')
            if datetime.date.today() >= datetime.datetime.strptime(cancel_date, '%Y-%m-%d').date():
                message = 'Please select a date greater than today.'
                context['message'] = message
                return render(request, 'students/meal_cancel.html',context)
            BaseMealPrecancellation.objects.create(rollno=request.user.rollno, date=cancel_date, time=cancel_time)
            message = 'Meal cancellation is successful.'
            context['message'] = message
            return render(request, 'students/meal_cancel.html',context)
        return render(request, 'students/meal_cancel.html',context)
    else:
            return HttpResponseForbidden("You are not authorized to access this page.")

from datetime import datetime


def extra_booking(request, rollno):
    if request.method == 'POST':
        extra_date = request.POST.get('extraDate')
        extra_time = request.POST.get('extraTime')
        
        # Get the day of the week for the selected date
        day_of_week = datetime.strptime(extra_date, '%Y-%m-%d').strftime('%A')
        
        # Fetch weekly items for the selected day of the week
        weekly_items = ExtraItem.objects.filter(Day=day_of_week, Type='Weekly')
        
        # Fetch special items for the selected date and time
        special_items = ExtraItem.objects.filter(Date=extra_date, Type='Special')
        
        # Fetch regular items for the selected date and time
        regular_items = ExtraItem.objects.filter(Date=extra_date, Time=extra_time, Type='Regular')
        
        # Render the template with the retrieved items
        return render(request, 'students/meal_cancel.html', {'weekly_items': weekly_items,
                                                             'special_items': special_items,
                                                             'regular_items': regular_items})
    else:
        # Handle GET request (initial load of the page)
        return render(request, 'students/meal_cancel.html')
    

def show_extra(request,rollno):
    if not request.user.is_student and request.user.rollno != rollno and request.user.rollno == 0 :
            return HttpResponseForbidden("You are not authorized to access this page.")
    if request.method == 'POST':
        extra_date = request.POST.get('extraDate')
        extra_time = request.POST.get('extraTime')

        
        
        # Get the day of the week for the selected date
        day_of_week = datetime.strptime(extra_date, '%Y-%m-%d').strftime('%A').lower()
        
        # Fetch weekly items for the selected day of the week
        weekly_items = ExtraItem.objects.filter(Day=day_of_week, Type='weekly')
        
        # Fetch special items for the selected date and time
        special_items = ExtraItem.objects.filter(Date=extra_date,Time=extra_time , Type='special')
        
        # Fetch regular items for the selected date and time
        regular_items = ExtraItem.objects.filter(Type='regular')

        request.session['extraDate'] = extra_date
        request.session['extraTime'] = extra_time
        
        # Render the template with the retrieved items
        return render(request, 'students/show_extra.html', {'rollno': rollno,'weekly_items': weekly_items,
                                                             'special_items': special_items,
                                                             'regular_items': regular_items})

def book_extra_item(request, rollno):
    if not request.user.is_student and request.user.rollno != rollno and request.user.rollno == 0 :
            return HttpResponseForbidden("You are not authorized to access this page.")
    if request.method == 'POST':
        # Get data from the form
        extra_date = request.session.get('extraDate')
        extra_time = request.session.get('extraTime')
        extra_item_id = request.POST.get('extra_item')  # Assuming the value is the ID of the extra item

        # Save the data to the BookingExtraItems model
        booking_extra_item = BookingExtraItems(
            rollno=rollno,
            date=extra_date,
            time=extra_time,
            extra_item=extra_item_id
            # Add other fields if needed
        )
        booking_extra_item.save()


        # Optionally, you can redirect the user to a success page
        return redirect('meal_cancel',rollno=rollno)  # Replace 'success_page' with the URL name of your success page

    # Handle GET requests or invalid form submissions


def get_extra_items(request):
    date = request.GET.get('date')
    time = request.GET.get('time')

    # Retrieve extra items based on date and time
    extra_items = ExtraItem.objects.filter(Date=date, Time=time).values('id', 'name', 'price')

    # Return extra items as JSON response
    return JsonResponse(list(extra_items), safe=False)

def cancel_meal(request,rollno):
    if request.method == 'POST':
        cancel_date = request.POST.get('canceldate')
        cancel_time = request.POST.get('canceltime')
        if datetime.date.today() >= datetime.datetime.strptime(cancel_date, '%Y-%m-%d').date():
            message = 'Please select a date greater than today.'
            return redirect('base_meal_precancellation')
        BaseMealPrecancellation.objects.create(rollno=request.user.rollno, date=cancel_date, time=cancel_time)
        message = 'Meal cancellation is successful.'
        return redirect('base_meal_precancellation')
    return redirect('base_meal_precancellation')

class StudentCardView(View):
    def get(self, request, roll_number):
        student = Student.objects.get(roll_number=roll_number)
        form = StudentCardForm()  # You might want to initialize the form with initial data if needed
        return render(request, 'students/student_card.html', {'student': student, 'form': form})









 