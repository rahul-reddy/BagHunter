export function download(name: string, body: string, type = 'text/markdown;charset=utf-8') {
  const url = URL.createObjectURL(new Blob([body], {type}));
  const link = document.createElement('a'); link.href = url; link.download = name; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
