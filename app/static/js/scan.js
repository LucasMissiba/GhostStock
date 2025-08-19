function onScanSuccess(decodedText) {
  try {
    window.location.href = decodedText;
  } catch (e) {
    alert('QR Code inválido.');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('reader');
  const status = document.createElement('div');
  status.style.margin = '8px 0';
  status.textContent = 'Inicializando câmera...';
  container.parentNode.insertBefore(status, container.nextSibling);
  const html5QrCode = new Html5Qrcode('reader');
  const config = { fps: 10, qrbox: 250 };
  Html5Qrcode.getCameras().then(cameras => {
    if (!cameras || cameras.length === 0) {
      status.textContent = 'Nenhuma câmera encontrada';
      return;
    }
    const back = cameras.find(c => /back|traseira|rear/i.test(c.label)) || cameras[0];
    status.textContent = 'Câmera pronta. Aponte para o QR.';
    html5QrCode.start(back.id, config, (text) => {
      status.textContent = 'QR detectado. Redirecionando...';
      onScanSuccess(text);
    });
  }).catch(() => {
    status.textContent = 'Erro ao acessar a câmera';
  });
});





