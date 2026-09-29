# Technical Specification: Airgapped PPTX Generation, Storage, and Dual-Frontend Viewer

## 📋 1. Overview
This specification details the implementation of a Python-based PowerPoint generation and rendering pipeline that operates entirely within an airgapped network. 

**Key Constraints & Goals:**
*   **Prevent Git Bloat:** Raw `.pptx` files must never be committed to Git or saved locally to the server disk.
*   **Database Storage:** Files will be stored as binary data in a PostgreSQL database.
*   **Dual Frontend:** The payload must be served via a Django API to two separate frontends: a Django/Wagtail application and an internal GitHub Enterprise (GHE) Pages static site.
*   **Client-Side Rendering:** Both frontends will render the presentations client-side using `pptxgenjs-plus` (or a similar offline JavaScript `.pptx` viewer library).

---

## 🏗️ 2. Architecture Design

```text
                   ┌──────────────────────────────────────────┐
                   │        Python PPTX Generator             │
                   └────────────────────┬─────────────────────┘
                                        │ (Saves raw bytes)
                                        ▼
                   ┌──────────────────────────────────────────┐
                   │       PostgreSQL Database (BYTEA)        │
                   └────────────────────┬─────────────────────┘
                                        │ (Queries & Streams)
                                        ▼
                   ┌──────────────────────────────────────────┐
                   │            Django / Wagtail              │
                   └──────────┬────────────────────┬──────────┘
                              │                    │
          (Direct Template /  │                    │ (Cross-Origin Fetch / 
           Internal Routing)  │                    │  CORS-enabled Stream)
                              ▼                    ▼
                ┌─────────────────────────┐  ┌─────────────────────────┐
                │   Django Web App UI     │  │ GHE Pages Static Site   │
                └─────────────────────────┘  └─────────────────────────┘
```

---

## 🛠️ 3. Technical Requirements

### 3.1 Backend Data & Generation Pipeline (Python & PostgreSQL)
*   **Storage Strategy:** Store raw PowerPoint file bytes directly in a PostgreSQL table using the `BYTEA` data type. 
*   **In-Memory Generation:** Use `python-pptx` to build presentations inside an in-memory buffer (`io.BytesIO()`), extract the raw bytes, and write them directly to the database.
*   **Database Schema:**
    ```sql
    CREATE TABLE core_presentation (
        id SERIAL PRIMARY KEY,
        filename VARCHAR(255) NOT NULL,
        file_data BYTEA NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    ```

### 3.2 Django Model & API Endpoint
*   **Django Model:** Map the PostgreSQL table to a Django model. Use `models.BinaryField` to handle the `BYTEA` column.
*   **Streaming Controller/View:** Implement a Django view that handles fetching the `BinaryField` payload by its ID and streams it back via `FileResponse` with the proper MIME type (`application/vnd.openxmlformats-officedocument.presentationml.presentation`).
*   **CORS Policy (Airgapped Security):** Because the internal GHE Pages site operates on a different domain or port, the Django response must include an explicit `Access-Control-Allow-Origin` header matching the internal GHE Pages URL pattern to prevent browser cross-origin blocking.

### 3.3 Dual Frontend Rendering UI
*   **Offline Dependency Strategy:** Since the environment is airgapped, all JavaScript dependencies (`jquery`, `jszip`, and `pptxgenjs-plus` / `pptxjs` bundles) must be embedded locally.
*   **Django/Wagtail Client UI:** A template view pulling the stream URL directly using internal Django URL routing template tags.
*   **GitHub Enterprise Pages UI:** A static `index.html` page utilizing vanilla browser JavaScript (`fetch()`) to asynchronously target the absolute URL of the Django streaming endpoint, parse the blob into an Object URL, and render it.

---

## 💻 4. Reference Implementations

The following files represent the core components needed for this feature.

### 4.1. `generator.py` (Data Pipeline)
```python
import io
import psycopg2
from pptx import Presentation
from pptx.util import Inches

def generate_and_store_pptx(filename: str, db_connection_string: str):
    # 1. Initialize presentation in memory
    prs = Presentation()
    
    # Add a blank slide with a title
    title_slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(title_slide_layout)
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    
    title.text = "Airgapped Automated Report"
    subtitle.text = "Generated entirely in memory."

    # 2. Save presentation to an in-memory buffer
    pptx_buffer = io.BytesIO()
    prs.save(pptx_buffer)
    
    # Reset buffer cursor to the beginning before reading
    pptx_buffer.seek(0)
    binary_data = pptx_buffer.read()

    # 3. Connect to PostgreSQL and insert as BYTEA natively
    insert_query = """
        INSERT INTO core_presentation (filename, file_data)
        VALUES (%s, %s)
        RETURNING id;
    """
    
    try:
        conn = psycopg2.connect(db_connection_string)
        cursor = conn.cursor()
        
        # Execute binary insertion
        cursor.execute(insert_query, (filename, psycopg2.Binary(binary_data)))
        new_id = cursor.fetchone()[0]
        conn.commit()
        
        print(f"Successfully generated and stored '{filename}' with ID: {new_id}")
        
    except psycopg2.Error as e:
        print(f"Database error: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    DB_DSN = "dbname=mydb user=myuser password=mypassword host=localhost port=5432"
    generate_and_store_pptx("Q3_Financial_Report.pptx", DB_DSN)
```

### 4.2. `models.py` (Django Models)
```python
from django.db import models

class CorePresentation(models.Model):
    filename = models.CharField(max_length=255)
    file_data = models.BinaryField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'core_presentation'
        ordering = ['-created_at']

    def __str__(self):
        return self.filename
```

### 4.3. `views.py` (Django Streaming API)
```python
import io
from django.http import FileResponse, Http404
from django.views.decorators.http import require_GET
from .models import CorePresentation

@require_GET
def stream_presentation(request, pk):
    try:
        presentation = CorePresentation.objects.get(pk=pk)
    except CorePresentation.DoesNotExist:
        raise Http404("Presentation not found.")

    # Wrap the raw DB bytes in a BytesIO stream
    file_stream = io.BytesIO(presentation.file_data)
    
    # FileResponse handles streaming natively
    response = FileResponse(
        file_stream,
        as_attachment=False,  # Display inline/allow fetch parsing
        filename=presentation.filename,
        content_type='application/vnd.openxmlformats-officedocument.presentationml.presentation'
    )
    
    # Enforce Airgapped CORS - Allow ONLY the GHE Pages internal domain
    response['Access-Control-Allow-Origin'] = 'https://pages.github.internal.corp'
    response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    
    return response
```

### 4.4. `django_template.html` (Primary Frontend)
```html
{% load static %}
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Internal Django PPTX Viewer</title>
    <!-- Local CSS dependencies for Airgapped environment -->
    <link rel="stylesheet" href="{% static 'vendor/pptxjs/css/pptxjs.css' %}">
    <link rel="stylesheet" href="{% static 'vendor/pptxjs/css/nv.d3.min.css' %}">
</head>
<body>
    <div id="pptx-viewer-container" style="width: 100%; height: 800px;"></div>

    <!-- Local JS dependencies for Airgapped environment -->
    <script src="{% static 'vendor/jquery/jquery-3.6.0.min.js' %}"></script>
    <script src="{% static 'vendor/jszip/jszip.min.js' %}"></script>
    <script src="{% static 'vendor/pptxjs/js/pptxjs.min.js' %}"></script>

    <script>
        $(document).ready(function() {
            // Generate the internal Django URL dynamically
            const pptxStreamUrl = "{% url 'stream_presentation' pk=presentation_id %}";
            
            // Initialize rendering engine
            $("#pptx-viewer-container").pptxToHtml({
                pptxFileUrl: pptxStreamUrl,
                slidesScale: "100%",
                slideMode: false,
                keyBoardShortCut: false
            });
        });
    </script>
</body>
</html>
```

### 4.5. `ghe_pages_index.html` (Static Secondary Frontend)
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>GHE Pages PPTX Viewer</title>
    <!-- Local CSS dependencies deployed with the GHE static site -->
    <link rel="stylesheet" href="./libs/css/pptxjs.css">
    <link rel="stylesheet" href="./libs/css/nv.d3.min.css">
</head>
<body>
    <div id="pptx-viewer-container" style="width: 100%; height: 800px;">
        <p id="loading-text">Fetching presentation from API...</p>
    </div>

    <!-- Local JS dependencies deployed with the GHE static site -->
    <script src="./libs/js/jquery-3.6.0.min.js"></script>
    <script src="./libs/js/jszip.min.js"></script>
    <script src="./libs/js/pptxjs.min.js"></script>

    <script>
        $(document).ready(function() {
            // Hardcoded or dynamically injected absolute URL to the Django API
            const apiEndpoint = "https://api.internal.corp/presentations/stream/1/";
            
            // Fetch the binary stream to ensure CORS passes before rendering
            fetch(apiEndpoint, {
                method: 'GET',
                mode: 'cors'
            })
            .then(response => {
                if (!response.ok) throw new Error("Network response was not ok");
                return response.blob();
            })
            .then(blob => {
                // Remove loading text
                $("#loading-text").remove();

                // Create a temporary local object URL from the fetched blob data
                const fileObjectUrl = URL.createObjectURL(blob);
                
                // Initialize the pptxToHtml engine using the local blob reference
                $("#pptx-viewer-container").pptxToHtml({
                    pptxFileUrl: fileObjectUrl,
                    slidesScale: "100%",
                    slideMode: true,
                    keyBoardShortCut: true
                });
            })
            .catch(error => {
                $("#loading-text").text("Error loading presentation: " + error.message);
                console.error("Presentation fetch error:", error);
            });
        });
    </script>
</body>
</html>
```