import redis
import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from google.oauth2 import id_token
from google.auth.transport import requests
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from .serializers import RegisterSerializer, LoginSerializer
from .serializers import PetSphereUserSerializer, UserDataStoreSerializer
from .serializers import ChangePasswordSerializer, ResetPasswordSerializer
from user_profile.serializers import ProfileSerializer
from .models import PetSphereUser
from user_profile.models import Profile
from .utils.otp_utils import generate_otp, resend_otp, verify_otp
from .tasks import send_otp_email, send_password_otp_email

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0,
                                 decode_responses=True)


# ------------------------------ OTP Management ------------------------------
class SendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({"error": "Email is required"},
                            status=status.HTTP_400_BAD_REQUEST)
        otp, expiry_minutes = generate_otp(email)
        if otp:
            send_otp_email.delay(email, otp, expiry_minutes)
            return Response({"message": "OTP sent successfully"},
                            status=status.HTTP_200_OK)
        return Response({"error": "Failed to send otp, please try again"},
                        status=status.HTTP_400_BAD_REQUEST)


class ResendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({"error": "Email is required"},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            otp_entry, message = resend_otp(email)
            if otp_entry:
                otp = otp_entry.get("otp")
                expiry_minutes = otp_entry.get("expiry_minutes")
                send_otp_email.delay(email, otp, expiry_minutes)
                return Response({"message": "OTP resent successfully"},
                                status=status.HTTP_200_OK)
            else:
                return Response({"error": message},
                                status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')
        if not email or not otp:
            return Response({"error": "Email and OTP are required"},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            is_valid, message = verify_otp(email, otp)
            if is_valid:
                return Response({"message": "OTP verified successfully"},
                                status=status.HTTP_200_OK)
            else:
                return Response({"error": message},
                                status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ---------------------------- User Authentication ----------------------------
class UserDataStoreView(APIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [AllowAny()]
        elif self.request.method == 'GET':
            return [IsAuthenticated()]
        return super().get_permissions()

    def post(self, request):
        user_data = request.data.get('user_data')
        if not user_data:
            return Response({"error": "User Data is required"},
                            status=status.HTTP_400_BAD_REQUEST)
        email = request.data.get('email')
        if not email:
            return Response({"error": "Email is required"},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            serializer = UserDataStoreSerializer(data=user_data)
            if serializer.is_valid():
                redis_key = f"user_data:{email}"
                redis_client.set(redis_key, json.dumps(user_data))
                redis_client.expire(redis_key, 1200)
                return Response({"message": "User data stored successfully"},
                                status=status.HTTP_201_CREATED)
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request):
        try:
            username = request.user.username
            if not username:
                return Response({"error": "Username is required"},
                                status=status.HTTP_400_BAD_REQUEST)
            redis_key = f"user_data:{username}"
            user_data = redis_client.get(redis_key)
            if not user_data:
                return Response({"error": "User Data not found"},
                                status=status.HTTP_404_NOT_FOUND)
            return Response({"user_data": user_data.decode('utf-8')},
                            status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def validateUser(request):
    username = request.data.get('username')
    if not username:
        return Response({"error": "Username is required"},
                        status=status.HTTP_400_BAD_REQUEST)
    try:
        user = PetSphereUser.objects.get(username)
        if user.is_staff:
            return Response({"user_type": "admin"},
                            status=status.HTTP_200_OK)
        return Response({"user_type": "user"},
                        status=status.HTTP_200_OK)
    except PetSphereUser.DoesNotExist:
        return Response({"error": "User not found"},
                        status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([AllowAny])
def check_username(request):
    username = request.data.get('username', '').strip()
    if not username:
        return Response({"error": "Username is required."},
                        status=status.HTTP_400_BAD_REQUEST)
    if not username.isalnum() and '_' not in username:
        return Response(
            {
                "error": (
                    "Username can only contain letters, numbers, "
                    "and underscores."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(username) < 3 or len(username) > 15:
        return Response(
            {
                "error": "Username must be between 3 and 15 characters."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    is_available = not PetSphereUser.objects.filter(
        username__iexact=username).exists()
    return Response({"available": is_available})


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            email = request.data.get('email')
            username = request.data.get('username')
            if not email:
                return Response({"error": "Email is required"},
                                status=status.HTTP_)

            redis_key = f"user_data:{email}"
            user_data = redis_client.get(redis_key)

            if not user_data:
                return Response({"error": "User Data not found"},
                                status=status.HTTP_404_NOT_FOUND)
            user_data = json.loads(user_data)
            user_data['username'] = username

            serializer = RegisterSerializer(data=user_data)
            if serializer.is_valid():
                user = serializer.save()
                profile = user.profile
                profile_data = ProfileSerializer(
                    profile,
                    context={'request': request}).data
                refresh = RefreshToken.for_user(user)
                redis_client.delete(redis_key)
                return Response({
                    "message": "User registered successfully",
                    "profile": profile_data,
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                }, status=status.HTTP_201_CREATED)

            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data
            refresh = RefreshToken.for_user(user)
            profile = Profile.objects.get(user__id=user.id)
            profile_data = ProfileSerializer(
                profile,
                context={'request': request}).data
            return Response({
                "profile": profile_data,
                "refresh": str(refresh),
                "access": str(refresh.access_token)
            }, status=status.HTTP_200_OK)
        return Response({"error": "Invalid Credentials"},
                        status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh_token"]
            email = request.data["email"]
            if not refresh_token:
                return Response({"error": "Refresh token is required"},
                                status=status.HTTP_400_BAD_REQUEST)
            token = RefreshToken(refresh_token)
            token.blacklist()
            redis_key = f"user_data:{email}"
            redis_client.delete(redis_key)
            return Response({"message": "Successfully logged out"},
                            status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ---------------------------- Password Management ----------------------------
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={'request': request}
            )

        if serializer.is_valid():
            serializer.save()
            return Response({'success': 'Password changed successfully'},
                            status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ForgotPassword(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        is_username = request.data.get('is_username')

        if is_username:
            username = request.data.get('username')
            try:
                user = PetSphereUser.objects.get(username=username)
                if user:
                    email = user.email
                    otp = generate_otp(email)
                    send_password_otp_email(email, otp)
            except PetSphereUser.DoesNotExist:
                return Response({"error": "User not found"},
                                status=status.HTTP_404_NOT_FOUND)


class ResetPassword(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        uid = request.data.get('uid')
        token = request.data.get('token')
        new_password = request.data.get('new_password')

        try:
            user = PetSphereUser.objects.get(pk=uid)
        except PetSphereUser.DoesNotExist:
            return Response({"error": "Invalid user ID"},
                            status=status.HTTP_400_BAD_REQUEST)

        token_generator = PasswordResetTokenGenerator()
        if not token_generator.check_token(user, token):
            return Response({'error': 'Invalid or expired token'},
                            status=status.HTTP_400_BAD_REQUEST)
        serializer = ResetPasswordSerializer(
            data={'new_password': new_password}
            )
        if serializer.is_valid():
            serializer.save(user=user)
            return Response({'success': 'Password reset successfull'},
                            status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)


# -------------------------- User Profile & Settings --------------------------
class UserProfileViews(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = PetSphereUserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        user = request.user
        serializer = PetSphereUserSerializer(
            user, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            profile = user.profile
            profile_serializer = ProfileSerializer(
                profile, data=request.data, partial=True,
                context={'request': request}
            )
            if profile_serializer.is_valid():
                profile_serializer.save()
                return Response(profile_serializer.data,
                                status=status.HTTP_200_OK)
            return Response(profile_serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ----------------------- Security & Account Management -----------------------
class DeactivateAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        user = request.user

        user.is_active = False
        user.save()
        return Response({'success': 'Account deactivated successfully'},
                        status=status.HTTP_200_OK)


class ReactivateAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        user = request.user

        user.is_active = True
        user.save()
        return Response({'success': 'Account reactivated successfully'})


# ----------------------- Google Authentication -----------------------
class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get('token')
        if not token:
            return Response({'error': 'Token is required'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            google_client_id = settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY
            idinfo = id_token.verify_oauth2_token(token, requests.Request(),
                                                  google_client_id)
            email = idinfo['email']
            name = idinfo.get('name', '')

            user = PetSphereUser.objects.filter(email=email).first()

            if not user:
                email_prefix = email.split('@')[0]
                base_username = email_prefix
                username = base_username
                counter = 0
                while PetSphereUser.objects.filter(username=username).exists():
                    username = f"{base_username}_{counter}"
                    counter += 1

                user, created = PetSphereUser.objects.get_or_create(
                    username=username,
                    email=email,
                    defaults={'name': name}
                )

            profile, created_profile = Profile.objects.get_or_create(user=user)

            profile_data = ProfileSerializer(
                profile,
                context={'request': request}).data

            refresh = RefreshToken.for_user(user)
            return Response({
                'profile': profile_data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'email': str(email),
            }, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': 'Invalid token', 'details': str(e)},
                            status=status.HTTP_400_BAD_REQUEST)
