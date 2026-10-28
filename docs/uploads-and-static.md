# Uploads and static files

## multipart/form-data

```python
@app.post("/upload")
def upload(request):
    form = request.multipart()
    title = form.fields.get("title", "")
    photo = form.files["photo"]           # UploadedFile
    path = photo.save("uploads")          # sanitised name, stays inside "uploads/"
    return {"saved": path.name, "bytes": photo.size}, 201
```

`MultipartForm` has `fields` (text values), `files` (name to `UploadedFile`; the last
file wins for repeated names) and `all_files` (every `(field, UploadedFile)` pair).

`UploadedFile`: `filename` (as sent, never trust it), `safe_filename`, `content_type`
(as sent by the client, also untrusted), `data`, `size`, `save(directory, filename=None)`.

Limits and notes:

- The body is held in memory; cap it with `Config(max_request_size=...)` (413 beyond that).
- Check `size` and an allow-list of types; sniff content if it matters.
- At most 1000 parts per request; malformed bodies give `400`.

## Serving a directory

```python
app.static("/assets", "public")                     # GET /assets/app.css, GET /assets/ -> index.html
app.static("/", "site", index="index.html", max_age=600)
```

- `ETag` and `Last-Modified` on every file; `If-None-Match` / `If-Modified-Since` give `304`.
- `Cache-Control: public, max-age=<max_age>` (default 3600).
- Directory requests serve `index` (disable with `index=None`).
- `../` and percent-encoded traversal return `404`.
- `HEAD` works through the `GET` route. Range requests are not supported.

`app.static()` returns the `StaticFiles` object, which you can also use directly
(`files.serve(request, "path/inside/root")`) from your own handler.

For one-off files use `nexusserver.utils.paths.safe_join(root, user_path)`, which raises
`ValueError` if the result would leave `root`.
