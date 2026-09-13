import json
import os

import requests

from django.core.serializers import python
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db.models import Sum

from google import genai
from google.genai import types

from core.models import Crop
from django.db.models import Sum, Avg
from django.http import JsonResponse

def home(request):
    if request.user.is_authenticated:
        user_crops = Crop.objects.filter(user=request.user).order_by('-id')
        total_crops = user_crops.count()
        active_crops = user_crops.exclude(status__in=['Completed', 'Inactive']).count()
        total_hectares = user_crops.aggregate(total_hectares=Sum('hectares'))['total_hectares'] or 0
        latest_crop = user_crops.first()
        recent_crops = user_crops[:5]
        average_health = user_crops.aggregate(
    avg_health=Avg('health')
)['avg_health'] or 0

        return render(
            request,
            'newcrop.html',
            {
                'user_crops': user_crops,
                'total_crops': total_crops,
                'active_crops': active_crops,
                'total_hectares': total_hectares,
                'latest_crop': latest_crop,
                'recent_crops': recent_crops,
                'average_health': average_health,
                'health_data': [crop.health for crop in user_crops],
            }
        )

    return render(request, 'newcrop.html')


def register_view(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password1', '')
        confirm_password = request.POST.get('password2', '')

        # Required fields validation
        if not full_name or not email or not username or not password:
            messages.error(request, 'Please fill all required fields.')
            return redirect('/#register')

        # Email validation
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, 'Please enter a valid email address.')
            return redirect('/#register')

        # Password confirmation
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return redirect('/#register')

        # Username duplicate check
        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('/#register')

        # Email duplicate check
        if User.objects.filter(email__iexact=email).exists():
            messages.error(request, 'Email already exists.')
            return redirect('/#register')

        # Create user securely
        User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=full_name
        )

        messages.success(
            request,
            'Account created successfully. Please login.'
        )

        return redirect('/#login')

    return redirect('/#register')


def login_view(request):
    if request.method == 'POST':
        login_input = request.POST.get('loginEmail', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(
            request,
            username=login_input,
            password=password
        )

        if user is None and '@' in login_input:
            account = User.objects.filter(
                email__iexact=login_input
            ).first()

            if account is not None:
                user = authenticate(
                    request,
                    username=account.username,
                    password=password
                )

        if user is not None:
            login(request, user)
            return redirect('/#dashboard')

        messages.error(
            request,
            'Invalid username/email or password.'
        )

        return redirect('/#login')

    return redirect('/#login')


@login_required
def new_crop(request):
    if request.method == 'POST':
        crop_name = request.POST.get('crop_name', '').strip()
        crop_type = request.POST.get('crop_type', '').strip()
        hectares = request.POST.get('hectares', '').strip()

        if not crop_name or not crop_type or not hectares:
            messages.error(request, 'Please fill all required crop fields.')
            return redirect('/#new-crop')

        try:
            hectares_value = float(hectares)
        except (TypeError, ValueError):
            messages.error(request, 'Please enter a valid hectares value.')
            return redirect('/#new-crop')

        Crop.objects.create(
            user=request.user,
            crop_name=crop_name,
            crop_type=crop_type,
            hectares=hectares_value,
            health=0,
            disease_risk=0,
            pest_risk=0,
            status='Pending'
        )

        messages.success(request, 'Crop added successfully.')
        return redirect('/#dashboard')

    return render(request, 'newcrop.html')


@login_required
def edit_crop(request, crop_id):
    crop = get_object_or_404(
        Crop,
        id=crop_id,
        user=request.user
    )

    if request.method == 'POST':
        crop_name = request.POST.get('crop_name', '').strip()
        crop_type = request.POST.get('crop_type', '').strip()
        hectares = request.POST.get('hectares', '').strip()
        health = request.POST.get('health', '0').strip()
        disease_risk = request.POST.get('disease_risk', '0').strip()
        pest_risk = request.POST.get('pest_risk', '0').strip()
        status = request.POST.get('status', 'Pending').strip()

        if not crop_name or not crop_type or not hectares:
            messages.error(request, 'Please fill all required crop fields.')
            return redirect('/#my-crops')

        try:
            hectares_value = float(hectares)
            health_value = int(health or 0)
            disease_risk_value = int(disease_risk or 0)
            pest_risk_value = int(pest_risk or 0)

            if not 0 <= health_value <= 100:
                raise ValueError

            if not 0 <= disease_risk_value <= 100:
                raise ValueError

            if not 0 <= pest_risk_value <= 100:
                raise ValueError

        except (TypeError, ValueError):
            messages.error(request, 'Please enter valid crop values.')
            return redirect('/#my-crops')

        crop.crop_name = crop_name
        crop.crop_type = crop_type
        crop.hectares = hectares_value
        crop.health = health_value
        crop.disease_risk = disease_risk_value
        crop.pest_risk = pest_risk_value
        crop.status = status or 'Pending'
        crop.save()

        messages.success(request, 'Crop updated successfully.')
        return redirect('/#dashboard')

    return redirect('/#my-crops')


@login_required
def delete_crop(request, crop_id):
    crop = get_object_or_404(
        Crop,
        id=crop_id,
        user=request.user
    )

    if request.method == 'POST':
        crop.delete()
        messages.success(request, 'Crop deleted successfully.')

    return redirect('/#dashboard')


def logout_view(request):
    logout(request)
    return redirect('/#login')


def weather_view(request):
    city = request.GET.get('city', 'Rajkot').strip() or 'Rajkot'

    api_key = os.environ.get("OPENWEATHER_API_KEY")

    if not api_key:
        return JsonResponse(
            {
                'success': False,
                'message': 'Weather API key is not configured.'
            },
            status=500
        )

    try:
        response = requests.get(
            'https://api.openweathermap.org/data/2.5/weather',
            params={
                'q': city,
                'appid': api_key,
                'units': 'metric'
            },
            timeout=10
        )

        if response.status_code == 404:
            return JsonResponse(
                {
                    'success': False,
                    'message': 'City not found.'
                },
                status=404
            )

        response.raise_for_status()

        weather_data = response.json()

        if not isinstance(weather_data, dict):
            raise ValueError('Invalid weather response format.')

        weather = (weather_data.get('weather') or [{}])[0]
        main = weather_data.get('main') or {}
        wind = weather_data.get('wind') or {}
        sys_data = weather_data.get('sys') or {}

        if not all(
            [
                weather_data.get('name'),
                sys_data.get('country'),
                main.get('temp') is not None,
                main.get('feels_like') is not None,
                main.get('humidity') is not None,
                main.get('pressure') is not None,
                wind.get('speed') is not None,
                weather.get('description'),
                weather.get('main'),
                weather.get('icon')
            ]
        ):
            raise ValueError('Missing weather data fields.')

        return JsonResponse(
            {
                'success': True,
                'weather': {
                    'city': weather_data.get('name'),
                    'country': sys_data.get('country'),
                    'temperature': main.get('temp'),
                    'feels_like': main.get('feels_like'),
                    'humidity': main.get('humidity'),
                    'pressure': main.get('pressure'),
                    'wind_speed': wind.get('speed'),
                    'description': weather.get('description'),
                    'weather_main': weather.get('main'),
                    'icon': weather.get('icon')
                }
            }
        )

    except requests.exceptions.Timeout:
        return JsonResponse(
            {
                'success': False,
                'message': 'Weather service timed out.'
            },
            status=504
        )

    except requests.exceptions.HTTPError:
        return JsonResponse(
            {
                'success': False,
                'message': 'Weather service is temporarily unavailable.'
            },
            status=502
        )

    except requests.exceptions.RequestException:
        return JsonResponse(
            {
                'success': False,
                'message': 'Weather service is temporarily unavailable.'
            },
            status=502
        )

    except Exception:
        return JsonResponse(
            {
                'success': False,
                'message': 'Weather service is temporarily unavailable.'
            },
            status=502
        )


@login_required
def analyze_crop(request):
    if request.method != 'POST':
        return JsonResponse(
            {
                'success': False,
                'message': 'Only POST requests are allowed.'
            },
            status=405
        )

    image = request.FILES.get('image')

    if not image:
        return JsonResponse(
            {
                'success': False,
                'message': 'Please upload a crop image.'
            },
            status=400
        )

    allowed_types = [
        'image/jpeg',
        'image/png',
    ]

    if image.content_type not in allowed_types:
        return JsonResponse(
            {
                'success': False,
                'message': 'Only JPG, JPEG and PNG images are allowed.'
            },
            status=400
        )

    # Maximum file size: 5 MB
    if image.size > 5 * 1024 * 1024:
        return JsonResponse(
            {
                'success': False,
                'message': 'Image size must be less than 5 MB.'
            },
            status=400
        )

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        return JsonResponse(
            {
                'success': False,
                'message': 'Gemini API key is not configured.'
            },
            status=500
        )

    response_text = ''

    try:
        image_bytes = image.read()

        if not image_bytes:
            return JsonResponse(
                {
                    'success': False,
                    'message': 'Unable to process uploaded image.'
                },
                status=400
            )

        model_name = 'gemini-3.6-flash'
        prompt = (
            "Analyze ONLY the uploaded crop/plant image.\n\n"
            "Identify the most likely crop visible in the image.\n"
            "Assess visible overall plant health.\n"
            "Assess visible disease risk based ONLY on visual evidence.\n"
            "Assess visible pest risk based ONLY on visual evidence.\n"
            "Do not invent diseases, pests, symptoms, or crop information that cannot reasonably be supported by the image.\n"
            "If the image is blurry, unrelated, too dark, contains no recognizable crop/plant, or cannot be reliably analyzed, return Unknown Crop and Unable to Analyze.\n\n"
            "Return a valid JSON object with exactly these fields:\n"
            "{\n"
            '"crop_name": "string",\n'
            '"health": integer,\n'
            '"disease_risk": integer,\n'
            '"pest_risk": integer,\n'
            '"status": "string"\n'
            "}\n\n"
            "Rules:\n"
            "crop_name:\n"
            "Most likely crop name.\n"
            "If uncertain: \"Unknown Crop\"\n\n"
            "health:\n"
            "Integer 0-100.\n"
            "100 means visibly very healthy.\n"
            "0 means unable to assess or extremely unhealthy.\n\n"
            "disease_risk:\n"
            "Integer 0-100.\n"
            "Based only on visible disease indicators.\n\n"
            "pest_risk:\n"
            "Integer 0-100.\n"
            "Based only on visible pest indicators.\n\n"
            "status:\n"
            "Use one concise status:\n"
            "Healthy\n"
            "Needs Attention\n"
            "Disease Suspected\n"
            "Pest Suspected\n"
            "Critical\n"
            "Unable to Analyze\n\n"
            "If the image cannot be reliably analyzed, return:\n"
            "{\n"
            '"crop_name": "Unknown Crop",\n'
            '"health": 0,\n'
            '"disease_risk": 0,\n'
            '"pest_risk": 0,\n'
            '"status": "Unable to Analyze"\n'
            "}"
        )

        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model=model_name,
            contents=[
                types.Part.from_text(text=prompt),
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=image.content_type
                )
            ],
            config=types.GenerateContentConfig(
                response_mime_type='application/json'
            )
        )

        response_text = getattr(response, 'text', '') or ''

        if response_text:
            response_text = response_text.strip()

        if not response_text:
            candidates = getattr(response, 'candidates', None) or []
            for candidate in candidates:
                parts = getattr(candidate, 'content', None)
                if parts is None:
                    continue
                content_parts = getattr(parts, 'parts', None) or []
                for part in content_parts:
                    part_text = getattr(part, 'text', '') or ''
                    if part_text:
                        response_text = part_text.strip()
                        break
                if response_text:
                    break

        if response_text.startswith('```'):
            response_text = response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[len('```json'):]
            elif response_text.startswith('```'):
                response_text = response_text[len('```'):]
            if response_text.endswith('```'):
                response_text = response_text[:-len('```')]
            response_text = response_text.strip()

        if not response_text:
            raise ValueError('Gemini returned an empty response.')

        try:
            parsed_response = json.loads(response_text)
        except json.JSONDecodeError:
            start_index = response_text.find('{')
            if start_index == -1:
                raise

            candidate_text = response_text[start_index:]
            parsed_response, _ = json.JSONDecoder().raw_decode(candidate_text)

        required_keys = [
            'crop_name',
            'health',
            'disease_risk',
            'pest_risk',
            'status'
        ]

        if not isinstance(parsed_response, dict):
            raise ValueError('Invalid AI response format.')

        for key in required_keys:
            if key not in parsed_response:
                raise ValueError('Missing required AI output fields.')

        crop_name = parsed_response.get('crop_name')
        if not isinstance(crop_name, str) or not crop_name.strip():
            raise ValueError('Invalid crop_name value.')

        status = parsed_response.get('status')
        if not isinstance(status, str) or not status.strip():
            raise ValueError('Invalid status value.')

        try:
            health = int(parsed_response.get('health', 0))
            disease_risk = int(parsed_response.get('disease_risk', 0))
            pest_risk = int(parsed_response.get('pest_risk', 0))
        except (TypeError, ValueError):
            raise ValueError('Invalid numeric AI output values.')

        if not 0 <= health <= 100:
            raise ValueError('Invalid health value.')

        if not 0 <= disease_risk <= 100:
            raise ValueError('Invalid disease risk value.')

        if not 0 <= pest_risk <= 100:
            raise ValueError('Invalid pest risk value.')

        crop_name = crop_name.strip()
        status = status.strip()

        allowed_statuses = {
            'Healthy',
            'Needs Attention',
            'Disease Suspected',
            'Pest Suspected',
            'Critical'
        }

        if status == 'Unable to Analyze':
            return JsonResponse(
                {
                    'success': False,
                    'message': 'Unable to analyze this crop image.'
                },
                status=400
            )

        if status not in allowed_statuses:
            raise ValueError('Invalid status value.')

        if crop_name.lower() == 'unknown crop':
            raise ValueError('Invalid crop_name value.')

        crop = Crop.objects.create(
            user=request.user,
            crop_name=crop_name,
            crop_type=crop_name,
            hectares=0,
            health=health,
            disease_risk=disease_risk,
            pest_risk=pest_risk,
            status=status
        )

        return JsonResponse(
            {
                'success': True,
                'saved': True,
                'result': {
                    'id': crop.id,
                    'crop_name': crop.crop_name,
                    'crop_type': crop.crop_type,
                    'hectares': crop.hectares,
                    'health': crop.health,
                    'disease_risk': crop.disease_risk,
                    'pest_risk': crop.pest_risk,
                    'status': crop.status
                }
            }
        )

    except Exception as exc:
        if response_text:
            print("Gemini raw response:", response_text)

        print("Gemini analysis error:", repr(exc))

        return JsonResponse(
            {
                'success': False,
                'message': f'Gemini error: {str(exc)}'
            },
            status=500
        )











