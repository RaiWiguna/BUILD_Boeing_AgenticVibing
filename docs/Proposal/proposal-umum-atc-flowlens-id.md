# Proposal Umum ATC FlowLens

## Gambaran Proyek

**ATC FlowLens** adalah konsep sistem pendukung keputusan yang bersifat explainable untuk operasi Air Traffic Control. Solusi ini dirancang untuk membantu controller, tim keselamatan bandara, dan pusat pelatihan memahami pergerakan runway, urutan pesawat, aktivitas kendaraan bandara, status komunikasi, dan risiko workload dalam satu tampilan operasional yang jelas.

Sistem ini tidak menggantikan air traffic controller. Perannya adalah mendukung pengambilan keputusan manusia dengan mengubah informasi operasional yang tersebar menjadi peringatan yang lebih awal, lebih jelas, dan lebih mudah dijelaskan.

## Primary Innovation Focus Area

**Focus Area yang dipilih: Advanced Technology and Innovation**

ATC FlowLens masuk ke area ini karena menerapkan konsep digital aviation yang lebih maju untuk menyelesaikan masalah nyata dalam operasi aerospace yang bersifat safety-critical. Ide ini menggabungkan data surveillance simulasi, pemodelan status runway, parsing komunikasi, perhitungan time-to-conflict, workload scoring, dan alert yang explainable.

Kemampuan tersebut sangat sesuai dengan inovasi pada sistem aviation berbasis human-in-the-loop, decision support, dan keselamatan operasi bandara.

Solusi ini juga dapat menciptakan dampak sosial melalui peningkatan keselamatan penerbangan dan mendukung sustainability dengan membantu mengurangi go-around dan delay yang tidak perlu. Namun, inovasi utamanya tetap berada pada sisi teknologi: membantu controller mendeteksi dan memahami risiko lebih cepat melalui asisten digital yang terintegrasi.

## Alignment with BUILD Indonesia Focus Area

ATC FlowLens selaras dengan tema **Aerospace & Defense** karena membahas runway safety, workload air traffic controller, dan kesiapan operasional bandara. Ketiganya merupakan isu penting dalam keselamatan penerbangan dan operasi infrastruktur kritis.

Proyek ini juga mendukung focus area **Advanced Technology and Innovation** karena menggunakan digital decision support, simulasi tracking pesawat dan kendaraan, rule-based conflict detection, workload scoring, serta alert yang explainable. Dalam konteks BUILD Indonesia, solusi ini relevan sebagai prototipe keselamatan penerbangan yang praktis dan dapat didemonstrasikan tanpa perlu mengakses data ATC live yang sensitif.

Solusi ini juga memiliki alignment sekunder dengan **Social Impact** dan **Sustainability**. Operasi runway yang lebih aman dapat melindungi penumpang, kru, tim ground, dan unit emergency bandara. Flow runway yang lebih baik juga dapat membantu mengurangi go-around, delay, dan fuel burn yang tidak perlu pada penggunaan operasional di masa depan.

## Problem Statement

Air Traffic Control adalah salah satu lingkungan kerja paling kompleks dalam dunia penerbangan. Controller harus memantau pesawat, status runway, kendaraan bandara, cuaca, komunikasi radio, flight strip, dan koordinasi dengan unit lain sambil membuat keputusan dalam hitungan detik.

Masalahnya bukan hanya jumlah pesawat di ruang udara. Workload controller dapat meningkat tajam ketika beberapa kondisi terjadi bersamaan, seperti low visibility, runway crossing aktif, kendaraan emergency, komunikasi radio yang padat, sequencing kedatangan pesawat, atau perubahan penggunaan runway secara tiba-tiba. Pada kondisi seperti ini, informasi penting sering tersebar di beberapa sistem dan percakapan radio. Akibatnya, controller lebih sulit menjaga situational awareness secara utuh.

Runway safety menjadi area yang sangat sensitif. Pesawat yang akan mendarat atau lepas landas dapat berkonflik dengan kendaraan di darat jika status clearance, pergerakan kendaraan, dan waktu kedatangan pesawat tidak dipahami sebagai satu konteks yang sama. Beberapa insiden nyata terkait runway incursion dan konflik antara pesawat dengan kendaraan menunjukkan bahwa rantai kecelakaan sering terbentuk dari kombinasi workload, celah komunikasi, tekanan waktu, dan kurangnya visibilitas operasional yang menyeluruh.

Teknologi ATC saat ini sudah memiliki safety net penting, seperti radar, ADS-B, surface surveillance, electronic flight strip, A-SMGCS, RIMCAS, STCA, dan data communication systems. Namun, tidak semua bandara memiliki tingkat peralatan yang sama. Selain itu, banyak sistem masih menuntut controller untuk menghubungkan informasi dari beberapa display dan komunikasi voice secara manual. Karena itu, dibutuhkan lapisan pendukung yang ringan dan explainable untuk membantu mengidentifikasi risiko konflik runway dan peningkatan workload sebelum situasi menjadi tidak aman.

## Proposed Solution / Idea

ATC FlowLens adalah dashboard decision-support dan training tool yang menyatukan pergerakan runway, urutan pesawat, aktivitas kendaraan ground, kejadian komunikasi, dan indikator workload ke dalam satu timeline operasional.

Untuk MVP hackathon, sistem ini dapat dikembangkan menggunakan data bandara simulasi, bukan sistem ATC live. Simulasi dapat memodelkan lingkungan runway dengan pesawat inbound, departure traffic, kendaraan bandara seperti fire truck atau inspection vehicle, clearance log, serta perubahan cuaca atau visibility.

Fitur utama yang diusulkan:

- **Runway Occupancy Monitoring**  
  Menampilkan apakah runway sedang clear, occupied, sedang diseberangi kendaraan, digunakan untuk takeoff, atau sedang menerima pesawat yang akan landing.

- **Aircraft and Vehicle Tracking**  
  Menampilkan posisi pesawat dan kendaraan bandara secara simulatif pada peta bandara sederhana.

- **Clearance State Engine**  
  Melacak status operasional seperti cleared to land, cleared for takeoff, hold short, line up and wait, cleared to cross, dan go around.

- **Time-to-Conflict Calculation**  
  Membandingkan estimasi waktu touchdown atau runway entry pesawat dengan estimasi waktu kendaraan menyeberang atau keluar dari runway.

- **Explainable Conflict Alert**  
  Memberikan alasan singkat di balik setiap alert, misalnya: "Vehicle clear time is later than aircraft touchdown time."

- **Communication Timeline**  
  Menyusun pesan ATC, pilot, dan kendaraan ke dalam riwayat kejadian yang mudah dibaca. Fitur ini dapat dikembangkan lebih lanjut dengan speech-to-text atau readback mismatch detection.

- **Controller Workload Indicator**  
  Mengestimasi workload berdasarkan jumlah traffic, radio call, clearance aktif, pergerakan kendaraan, kondisi cuaca, dan alert aktif.

- **Replay Mode for Training**  
  Memungkinkan pengguna melihat ulang timeline skenario konflik untuk memahami apa yang terjadi, kapan terjadi, dan mengapa sistem memberikan alert.

Nilai utama ATC FlowLens adalah explainability. Dalam lingkungan safety-critical, sebuah alert akan lebih berguna jika dapat menjelaskan alasan operasional di baliknya. Sistem ini tidak diposisikan sebagai autonomous controller. Perannya adalah mendukung awareness yang lebih cepat, pelatihan yang lebih baik, dan pengambilan keputusan yang lebih jelas sambil tetap menempatkan controller sebagai pengambil keputusan utama.

## Target Users / Market

ATC FlowLens ditujukan untuk organisasi dan tim yang terlibat dalam operasi bandara, air traffic management, runway safety, dan pelatihan penerbangan.

Pengguna utama:

- **Tower Controllers**  
  Mengelola takeoff, landing, runway occupancy, dan keputusan runway crossing.

- **Ground Controllers**  
  Mengatur taxi route pesawat, pergerakan kendaraan, permintaan runway crossing, dan surface safety.

- **Approach Controllers**  
  Mengatur sequencing pesawat inbound dan koordinasi handoff ke tower control.

- **Airport Operation Centers**  
  Memantau kondisi runway, aktivitas emergency response, dan gangguan operasional.

- **Airport Rescue and Firefighting Units**  
  Mengoperasikan kendaraan yang mungkin perlu bergerak dekat atau melintasi runway aktif, terutama saat latihan atau emergency.

- **ATC Training Centers**  
  Menggunakan sistem untuk mengajarkan workload awareness, pencegahan runway incursion, akurasi komunikasi, dan pengenalan konflik.

- **Aviation Safety Investigators**  
  Menggunakan tampilan replay untuk mempelajari timeline kejadian, urutan komunikasi, dan titik-titik pengambilan keputusan.

Pasar awal paling realistis adalah sebagai platform training, simulasi, dan safety-awareness untuk bandara, sekolah penerbangan, Air Navigation Service Provider, dan tim operasi bandara. Positioning ini lebih masuk akal karena sistem ATC operasional nyata membutuhkan sertifikasi ketat, validasi, tinjauan cybersecurity, dan persetujuan regulator. Produk yang dimulai dari simulasi tetap dapat memberi nilai kuat melalui peningkatan kualitas pelatihan, analisis keselamatan, dan kesiapan menghadapi skenario runway yang kompleks.

## Expected Impact

ATC FlowLens diharapkan dapat meningkatkan cara risiko runway safety dikenali, dijelaskan, dan dievaluasi dalam lingkungan simulasi atau pelatihan. Dengan menampilkan pergerakan pesawat, aktivitas kendaraan, status clearance, dan time-to-conflict dalam satu tampilan, sistem ini dapat membantu pengguna mengenali potensi konflik runway lebih awal.

Solusi ini juga dapat mengurangi kompleksitas pelatihan dengan memberikan timeline kejadian yang jelas, bukan hanya alert. Hal ini membuat controller dan tim keselamatan lebih mudah memahami mengapa konflik terjadi, faktor operasional apa yang berkontribusi, dan tindakan apa yang perlu dipertimbangkan.

Dalam jangka panjang, konsep ini dapat mendukung operasi runway yang lebih aman, workload awareness yang lebih baik, dan proses pembelajaran pasca-kejadian yang lebih efektif. Solusi ini juga dapat memberi manfaat sustainability secara tidak langsung dengan membantu mengurangi go-around, holding, taxi delay, dan konsumsi fuel yang tidak perlu pada versi operasional di masa depan.

## MVP Scope

Untuk prototipe awal, ATC FlowLens dapat dibangun dengan:

- satu layout bandara simulasi dengan runway dan taxiway
- tiga sampai lima pesawat simulasi
- satu atau dua kendaraan bandara
- clearance dan communication logs
- status cuaca atau visibility
- rule-based conflict detection
- time-to-conflict alerting
- workload scoring
- replay mode

Scope ini dapat dicapai tanpa menggunakan data ATC asli yang sensitif, tetapi tetap cukup kuat untuk menunjukkan konsep inovasi aerospace and defense yang kredibel.

## One-Line Summary

ATC FlowLens adalah dashboard decision-support yang explainable untuk membantu tim air traffic melihat risiko konflik runway, memahami workload controller, dan berlatih untuk operasi bandara yang lebih aman.
