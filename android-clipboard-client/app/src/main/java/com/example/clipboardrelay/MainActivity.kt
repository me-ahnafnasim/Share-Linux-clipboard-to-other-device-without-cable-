package com.example.clipboardrelay

import android.content.ContentValues
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Bundle
import android.os.Environment
import android.provider.MediaStore
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.example.clipboardrelay.databinding.ActivityMainBinding
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.text.DateFormat
import java.util.Date
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

class MainActivity : AppCompatActivity() {
    private lateinit var binding: ActivityMainBinding
    private val executor: ExecutorService = Executors.newSingleThreadExecutor()
    private var latestBitmap: Bitmap? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val savedUrl = getPreferences(MODE_PRIVATE).getString(PREF_SERVER_URL, DEFAULT_SERVER_URL)
        binding.serverUrlInput.setText(savedUrl)
        setStatus(getString(R.string.status_ready), isError = false)

        binding.fetchButton.setOnClickListener {
            fetchImage()
        }

        binding.downloadButton.setOnClickListener {
            saveLatestImage()
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        executor.shutdownNow()
    }

    private fun fetchImage() {
        val baseUrl = binding.serverUrlInput.text.toString().trim().trimEnd('/')
        if (baseUrl.isBlank()) {
            setStatus(getString(R.string.error_missing_url), isError = true)
            return
        }

        getPreferences(MODE_PRIVATE).edit().putString(PREF_SERVER_URL, baseUrl).apply()
        setLoading(true)
        setStatus(getString(R.string.status_fetching), isError = false)

        executor.execute {
            try {
                val bitmap = requestBitmap(baseUrl)
                runOnUiThread {
                    latestBitmap = bitmap
                    binding.previewImage.setImageBitmap(bitmap)
                    binding.previewImage.visibility = View.VISIBLE
                    binding.placeholderText.visibility = View.GONE
                    binding.downloadButton.isEnabled = true
                    binding.lastUpdatedText.text = getString(
                        R.string.last_updated,
                        DateFormat.getDateTimeInstance().format(Date())
                    )
                    setStatus(getString(R.string.status_success), isError = false)
                    setLoading(false)
                }
            } catch (error: IOException) {
                runOnUiThread {
                    latestBitmap = null
                    binding.previewImage.setImageDrawable(null)
                    binding.previewImage.visibility = View.GONE
                    binding.placeholderText.visibility = View.VISIBLE
                    binding.downloadButton.isEnabled = false
                    setStatus(error.message ?: getString(R.string.error_fetch_generic), isError = true)
                    setLoading(false)
                }
            }
        }
    }

    @Throws(IOException::class)
    private fun requestBitmap(baseUrl: String): Bitmap {
        val endpoint = "$baseUrl/api/image?t=${System.currentTimeMillis()}"
        val connection = (URL(endpoint).openConnection() as HttpURLConnection).apply {
            connectTimeout = 7000
            readTimeout = 15000
            requestMethod = "GET"
            setRequestProperty("Cache-Control", "no-cache")
            setRequestProperty("Pragma", "no-cache")
            useCaches = false
        }

        return connection.useConnection {
            val responseCode = it.responseCode
            if (responseCode != HttpURLConnection.HTTP_OK) {
                val message = it.errorStream?.bufferedReader()?.use { reader -> reader.readText() }
                throw IOException("Server error $responseCode${message?.let { text -> ": $text" } ?: ""}")
            }

            val bytes = it.inputStream.use { input -> input.readBytes() }
            BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
                ?: throw IOException(getString(R.string.error_decode))
        }
    }

    private fun saveLatestImage() {
        val bitmap = latestBitmap
        if (bitmap == null) {
            Toast.makeText(this, R.string.error_nothing_to_save, Toast.LENGTH_SHORT).show()
            return
        }

        executor.execute {
            try {
                val uri = saveBitmapToDownloads(bitmap)
                runOnUiThread {
                    Toast.makeText(
                        this,
                        getString(R.string.saved_to_downloads, uri.toString()),
                        Toast.LENGTH_LONG
                    ).show()
                }
            } catch (error: IOException) {
                runOnUiThread {
                    Toast.makeText(this, error.message, Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    @Throws(IOException::class)
    private fun saveBitmapToDownloads(bitmap: Bitmap): Uri {
        val filename = "clipboard-${System.currentTimeMillis()}.png"
        val values = ContentValues().apply {
            put(MediaStore.MediaColumns.DISPLAY_NAME, filename)
            put(MediaStore.MediaColumns.MIME_TYPE, "image/png")
            put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS)
            put(MediaStore.MediaColumns.IS_PENDING, 1)
        }

        val resolver = applicationContext.contentResolver
        val collection = MediaStore.Downloads.EXTERNAL_CONTENT_URI
        val uri = resolver.insert(collection, values)
            ?: throw IOException(getString(R.string.error_create_download))

        try {
            resolver.openOutputStream(uri)?.use { output ->
                if (!bitmap.compress(Bitmap.CompressFormat.PNG, 100, output)) {
                    throw IOException(getString(R.string.error_save_failed))
                }
            } ?: throw IOException(getString(R.string.error_save_failed))

            values.clear()
            values.put(MediaStore.MediaColumns.IS_PENDING, 0)
            resolver.update(uri, values, null, null)
            return uri
        } catch (error: Exception) {
            resolver.delete(uri, null, null)
            throw IOException(error.message ?: getString(R.string.error_save_failed), error)
        }
    }

    private fun setLoading(loading: Boolean) {
        binding.fetchButton.isEnabled = !loading
        binding.downloadButton.isEnabled = !loading && latestBitmap != null
        binding.progressBar.visibility = if (loading) View.VISIBLE else View.GONE
    }

    private fun setStatus(message: String, isError: Boolean) {
        binding.statusText.text = message
        binding.statusText.setTextColor(
            getColor(
                if (isError) R.color.status_error else R.color.status_ok
            )
        )
    }

    companion object {
        private const val PREF_SERVER_URL = "server_url"
        private const val DEFAULT_SERVER_URL = "http://192.168.1.10:5000"
    }
}

private inline fun <T> HttpURLConnection.useConnection(block: (HttpURLConnection) -> T): T {
    return try {
        block(this)
    } finally {
        disconnect()
    }
}
