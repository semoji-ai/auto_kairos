/* Shared bounded source preview for dashboard/Tauri and Adobe CEP.
   Viewing never changes track activation or image selection. */
(function () {
  if (window.initTrackPreviews) return;
  window.initTrackPreviews = function (root) {
    root.querySelectorAll(".track-preview").forEach(function (box) {
      var video = box.querySelector("video"), select = box.querySelector("select");
      if (!video || !select || video.dataset.trackWired) return;
      video.dataset.trackWired = "1";
      var start = 0, end = 0;
      function choose() {
        var option = select.options[select.selectedIndex];
        video.pause();
        start = Number(option.dataset.in); end = Number(option.dataset.out);
        video.muted = true;
        video.src = option.value;
        video.load();
      }
      video.addEventListener("loadedmetadata", function () { video.currentTime = start; });
      video.addEventListener("play", function () {
        if (video.currentTime < start || video.currentTime >= end - 0.001) video.currentTime = start;
      });
      video.addEventListener("seeking", function () {
        // Media clocks round to microseconds; exact comparisons can loop forever.
        if (video.currentTime < start - 0.001) video.currentTime = start;
        else if (video.currentTime > end + 0.001) video.currentTime = end;
      });
      video.addEventListener("timeupdate", function () {
        if (video.currentTime >= end) {
          video.pause();
          if (video.currentTime > end) video.currentTime = end;
        }
      });
      select.addEventListener("change", choose);
      choose();
    });
  };
})();
