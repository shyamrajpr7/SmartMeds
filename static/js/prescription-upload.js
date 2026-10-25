(function () {
  "use strict";

  var form = document.querySelector("form[data-max-upload-mb]");
  if (!form) {
    return;
  }

  var maxMb = parseFloat(form.getAttribute("data-max-upload-mb")) || 10;
  var maxBytes = maxMb * 1024 * 1024;
  var targetBytes = Math.min(1.6 * 1024 * 1024, maxBytes * 0.4);
  var compressThreshold = targetBytes;
  var maxDimension = 2200;
  var minQuality = 0.6;
  var submitButton = form.querySelector('button[type="submit"]');
  var fileInputs = form.querySelectorAll('input[type="file"]');
  var pending = 0;
  var formStatus = null;

  function formatMb(bytes) {
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  }

  function statusElement(input) {
    var id = "upload-status-" + (input.id || input.name || "file");
    var element = document.getElementById(id);
    if (!element) {
      element = document.createElement("div");
      element.id = id;
      element.className = "form-text";
      element.setAttribute("role", "status");
      element.setAttribute("aria-live", "polite");
      input.insertAdjacentElement("afterend", element);
    }
    return element;
  }

  function setStatus(input, message, isError) {
    var element = statusElement(input);
    element.textContent = message || "";
    if (isError) {
      element.classList.add("text-danger");
    } else {
      element.classList.remove("text-danger");
    }
  }

  function setBusy(delta) {
    pending += delta;
    if (pending < 0) {
      pending = 0;
    }
    if (submitButton) {
      submitButton.disabled = pending > 0;
    }
    form.setAttribute("aria-busy", pending > 0 ? "true" : "false");
  }

  function totalSize() {
    var total = 0;
    Array.prototype.forEach.call(fileInputs, function (input) {
      var file = input.files && input.files[0];
      if (file) {
        total += file.size;
      }
    });
    return total;
  }

  function formStatusElement() {
    if (!formStatus) {
      formStatus = document.createElement("div");
      formStatus.id = "upload-total-status";
      formStatus.className = "form-text";
      formStatus.setAttribute("role", "status");
      formStatus.setAttribute("aria-live", "polite");
      if (submitButton && submitButton.parentNode) {
        submitButton.parentNode.insertBefore(formStatus, submitButton);
      } else {
        form.appendChild(formStatus);
      }
    }
    return formStatus;
  }

  function setFormStatus(message, isError) {
    var element = formStatusElement();
    element.textContent = message || "";
    if (isError) {
      element.classList.add("text-danger");
    } else {
      element.classList.remove("text-danger");
    }
  }

  function refreshTotalStatus() {
    var total = totalSize();
    if (total > maxBytes) {
      setFormStatus(
        "Attachments total " +
          formatMb(total) +
          ". Please remove one or choose smaller files (max " +
          maxMb +
          " MB total per upload).",
        true
      );
    } else {
      setFormStatus("");
    }
  }

  function isImage(file) {
    return /^image\/(jpeg|png|webp)$/i.test(file.type);
  }

  function isPdf(file) {
    return (
      file.type === "application/pdf" || /\.pdf$/i.test(file.name || "")
    );
  }

  function loadImage(file) {
    return new Promise(function (resolve, reject) {
      var url = URL.createObjectURL(file);
      var image = new Image();
      image.onload = function () {
        URL.revokeObjectURL(url);
        resolve(image);
      };
      image.onerror = function () {
        URL.revokeObjectURL(url);
        reject(new Error("read-failed"));
      };
      image.src = url;
    });
  }

  function canvasToBlob(canvas, quality) {
    return new Promise(function (resolve) {
      canvas.toBlob(resolve, "image/jpeg", quality);
    });
  }

  function compressImage(file) {
    return loadImage(file).then(function (image) {
      var width = image.naturalWidth || image.width;
      var height = image.naturalHeight || image.height;
      var scale = Math.min(1, maxDimension / Math.max(width, height));
      var canvas = document.createElement("canvas");
      canvas.width = Math.max(1, Math.round(width * scale));
      canvas.height = Math.max(1, Math.round(height * scale));

      var context = canvas.getContext("2d");
      context.fillStyle = "#ffffff";
      context.fillRect(0, 0, canvas.width, canvas.height);
      context.drawImage(image, 0, 0, canvas.width, canvas.height);

      var quality = 0.85;

      function encode() {
        return canvasToBlob(canvas, quality).then(function (blob) {
          if (!blob) {
            throw new Error("encode-failed");
          }
          if (blob.size > targetBytes && quality > minQuality) {
            quality = Math.max(minQuality, quality - 0.1);
            return encode();
          }
          return blob;
        });
      }

      return encode().then(function (blob) {
        var name = (file.name || "prescription").replace(
          /\.[^.]+$/,
          ""
        );
        return new File([blob], name + ".jpg", {
          type: "image/jpeg",
          lastModified: Date.now(),
        });
      });
    });
  }

  function replaceFile(input, file) {
    var transfer = new DataTransfer();
    transfer.items.add(file);
    input.files = transfer.files;
  }

  function handleFile(input) {
    var file = input.files && input.files[0];
    setStatus(input, "");

    if (!file) {
      return;
    }

    if (isPdf(file) || !isImage(file)) {
      if (file.size > maxBytes) {
        setStatus(
          input,
          "This file is " +
            formatMb(file.size) +
            ". Please choose a file under " +
            maxMb +
            " MB.",
          true
        );
        input.value = "";
      } else {
        setStatus(input, formatMb(file.size) + " selected.");
      }
      return;
    }

    if (file.size <= compressThreshold) {
      setStatus(input, formatMb(file.size) + " selected.");
      return;
    }

    setBusy(1);
    setStatus(input, "Compressing " + formatMb(file.size) + " image...");

    compressImage(file)
      .then(function (compressed) {
        if (compressed.size > maxBytes) {
          setStatus(
            input,
            "This image could not be compressed below " +
              maxMb +
              " MB. Please choose a smaller image.",
            true
          );
          input.value = "";
          return;
        }

        try {
          replaceFile(input, compressed);
        } catch (error) {
          if (file.size > maxBytes) {
            setStatus(
              input,
              "This image is too large. Maximum size is " +
                maxMb +
                " MB.",
              true
            );
            input.value = "";
            return;
          }
        }

        setStatus(
          input,
          "Ready to upload: " +
            formatMb(compressed.size) +
            " (compressed from " +
            formatMb(file.size) +
            ")."
        );
      })
      .catch(function () {
        if (file.size > maxBytes) {
          setStatus(
            input,
            "This image could not be read. Please use a JPG, PNG, or WebP image under " +
              maxMb +
              " MB.",
            true
          );
          input.value = "";
        }
      })
      .finally(function () {
        setBusy(-1);
        refreshTotalStatus();
      });
  }

  Array.prototype.forEach.call(fileInputs, function (input) {
    input.addEventListener("change", function () {
      handleFile(input);
      refreshTotalStatus();
    });
  });

  form.addEventListener("submit", function (event) {
    if (pending > 0) {
      event.preventDefault();
      return;
    }

    var tooLarge = false;
    Array.prototype.forEach.call(fileInputs, function (input) {
      var file = input.files && input.files[0];
      if (!file) {
        return;
      }
      if (file.size > maxBytes) {
        tooLarge = true;
        setStatus(
          input,
          "This file is " +
            formatMb(file.size) +
            ". Maximum size is " +
            maxMb +
            " MB.",
          true
        );
      }
    });

    var total = totalSize();
    if (total > maxBytes) {
      tooLarge = true;
      setFormStatus(
        "Attachments total " +
          formatMb(total) +
          ". Please remove one or choose smaller files (max " +
          maxMb +
          " MB total per upload).",
        true
      );
    } else {
      setFormStatus("");
    }

    if (tooLarge) {
      event.preventDefault();
    }
  });
})();
