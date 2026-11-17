# Hướng dẫn test Spotify auth (Client Credentials + User login)

> Dùng cho repo `spotify-pipeline`. Chạy từ thư mục gốc repo, Git Bash trên Windows.

## 0. Hai loại token — dùng cái nào?

| Muốn gọi | Loại token | Cần trình duyệt? | Script |
|---|---|---|---|
| `/v1/tracks/{id}`, `/v1/artists/{id}`, `/v1/albums/{id}` (metadata cho pipeline) | Client Credentials | Không | `scripts/check_spotify.py` |
| `/v1/me`, `/v1/me/playlists`, `/v1/me/top/tracks` (dữ liệu của chính bạn) | Authorization Code (user login) | **Chỉ 1 lần** để lấy `refresh_token` | `scripts/spotify_login.py` → `scripts/check_spotify_user.py` |

Token Client Credentials gọi `/v1/me/...` **luôn trả 401** — đó là lỗi bạn gặp lúc đầu.

Callback `http://127.0.0.1:5000/callback` **không phải Spotify gọi vào máy bạn**: Spotify chỉ bảo *trình duyệt* chuyển trang sang đó kèm `?code=...`. Script `spotify_login.py` mở một server nhỏ ở cổng 5000 *chỉ trong lúc login* để tự bắt `code`. Sau khi có `refresh_token`, pipeline chạy hằng ngày **không cần server**.

## 1. Chuẩn bị Spotify Dashboard (1 lần)

1. Vào https://developer.spotify.com/dashboard → chọn app → **Settings** → **Edit**.
2. **Redirect URIs**: thêm **chính xác** `http://127.0.0.1:5000/callback` → **Add** → kéo xuống **Save**.
   - Không dùng `localhost`, không thừa `/` cuối, không `//callback`, đúng `http` (không `https`).
3. **User Management**: thêm email tài khoản Spotify bạn sẽ đăng nhập (Dev Mode: tối đa 5 user, tài khoản Premium).
4. Nếu client secret từng bị dán ra ngoài: **Rotate client secret** và cập nhật `.env`.

## 2. Cài môi trường

```bash
python -m venv .venv
source .venv/Scripts/activate      # Git Bash (PowerShell: .venv\Scripts\Activate.ps1)
python -m pip install -e ".[dev]"
```

`.env` (copy từ `.env.example` nếu chưa có) cần:

```
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
SPOTIFY_REDIRECT_URI=http://127.0.0.1:5000/callback
SPOTIFY_REFRESH_TOKEN=
```

## 3. Test offline (không gọi mạng)

```bash
pytest -q
```

Kỳ vọng: tất cả test pass (bao gồm `tests/test_spotify_auth.py`).

## 4. Test Client Credentials (metadata)

```bash
python scripts/check_spotify.py
```

Kỳ vọng:
```
OK token: type=Bearer expires_in=3600s
OK track: The Killers – Mr. Brightside (003vvx7Niy0yvhvHt4a68B)
Spotify smoke-check passed.
```

## 5. Login 1 lần để lấy refresh_token

```bash
python scripts/spotify_login.py --save
```

1. Trình duyệt tự mở trang Spotify → đăng nhập → **Agree**.
2. Trình duyệt hiện "Đã nhận code. Quay lại terminal."
3. Terminal in `OK access_token…`, `OK scope…`, và ghi `SPOTIFY_REFRESH_TOKEN` vào `.env`.

Không muốn mở server? `python scripts/spotify_login.py --no-server` → sau khi Agree, trang báo "can't be reached" là bình thường; copy **nguyên URL** trên thanh địa chỉ dán vào terminal.

## 6. Test API của user (không cần trình duyệt nữa)

```bash
python scripts/check_spotify_user.py
```

Kỳ vọng:
```
OK refresh → access_token expires_in=3600s
OK /me: <tên> (<user id>) product=premium
OK /me/playlists: N / total=N
  - <playlist id> | <tên playlist> | owner=<id>
Spotify user smoke-check passed.
```

### 6.1. Curl / Postman (cùng logic `check_spotify_user.py`)

Các call này tương đương `_get(...)` trong script: `GET https://api.spotify.com/v1{path}` + header `Authorization: Bearer <USER_ACCESS_TOKEN>`.

**Bắt buộc dùng user access token** (từ `grant_type=refresh_token`). Token Client Credentials gọi `/v1/me` → **401**.

Đây là smoke **user API** local — pipeline enrich metadata theo SPEC vẫn dùng Client Credentials; không đồng nghĩa Charts `auth/v0`.

#### A) Lấy access token (refresh)

```bash
curl -sS -X POST "https://accounts.spotify.com/api/token" \
  -u "<SPOTIFY_CLIENT_ID>:<SPOTIFY_CLIENT_SECRET>" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=refresh_token" \
  -d "refresh_token=<SPOTIFY_REFRESH_TOKEN>"
```

Copy `access_token` từ JSON. Nếu response có **`refresh_token` mới**, cập nhật `.env` (chạy lại `python scripts/spotify_login.py --save`) — nếu không, refresh sau này có thể `invalid_grant`.

#### B) GET giống script

```bash
# Profile — path "/me"
curl -sS -H "Authorization: Bearer <USER_ACCESS_TOKEN>" \
  "https://api.spotify.com/v1/me"

# Playlists — path "/me/playlists?limit=50"
curl -sS -H "Authorization: Bearer <USER_ACCESS_TOKEN>" \
  "https://api.spotify.com/v1/me/playlists?limit=50"
```

#### C) Postman

1. **POST** `https://accounts.spotify.com/api/token`
   - Auth: Basic Auth → Username = Client ID, Password = Client Secret  
     (hoặc header `Authorization: Basic …` tương đương `-u`)
   - Body → `x-www-form-urlencoded`:
     - `grant_type` = `refresh_token`
     - `refresh_token` = giá trị trong `.env`
   - Send → copy `access_token` (không commit / không dán secret thật vào doc).
2. **GET** `https://api.spotify.com/v1/me`  
   Auth → Bearer Token → dán `access_token`.
3. **GET** `https://api.spotify.com/v1/me/playlists?limit=50`  
   Auth → Bearer Token (cùng token).

Placeholders only: `<SPOTIFY_CLIENT_ID>`, `<SPOTIFY_CLIENT_SECRET>`, `<SPOTIFY_REFRESH_TOKEN>`, `<USER_ACCESS_TOKEN>`.

## 7. Bảng lỗi thường gặp

| Lỗi | Ở bước | Nguyên nhân | Cách sửa |
|---|---|---|---|
| `INVALID_CLIENT: Invalid redirect URI` / `redirect_uri: Not matching configuration` | Trang Spotify (bước 5) | URI trong Dashboard khác `SPOTIFY_REDIRECT_URI` dù 1 ký tự | Sửa Dashboard → **Save**, hoặc sửa `.env` cho khớp |
| `INVALID_CLIENT: Insecure redirect URI` | Trang Spotify | Dùng `localhost` hoặc `http` với domain thật | Dùng `http://127.0.0.1:<port>/...` |
| `invalid_grant` | Đổi code | Code đã dùng/hết hạn, hoặc redirect_uri khác lần authorize | Chạy lại `spotify_login.py` |
| `invalid_client` | Token | Sai client id/secret (hoặc secret đã rotate) | Cập nhật `.env` |
| `không mở được server 127.0.0.1:5000` | Bước 5 | Cổng 5000 đang bị chiếm | Tắt app đang dùng cổng hoặc dùng `--no-server` |
| HTTP 401 ở `/v1/me/...` | Bước 6 / curl | Dùng token Client Credentials, hoặc token hết hạn (1h) | Dùng token từ refresh_token |
| HTTP 403 ở `/v1/me/...` | Bước 6 | Tài khoản chưa có trong User Management / thiếu scope / chưa Premium | Thêm user vào Dashboard, chạy lại login |
| `SPOTIFY_REFRESH_TOKEN is empty` | Bước 6 | Chưa login | Làm bước 5 |

## 8. Bảo mật

- `.env` đã nằm trong `.gitignore`; **không** commit client secret / refresh token.
- Scripts không in client secret và chỉ in 8 ký tự đầu của access token.
- Muốn thu hồi quyền: https://www.spotify.com/account/apps/ → Remove access, hoặc rotate client secret.
