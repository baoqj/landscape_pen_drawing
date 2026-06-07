# Examples

示例输入图片放在项目根目录的 `../../pics` 下。运行：

```bash
python ../main.py --input ../../../pics/01.jpeg --output ../outputs/01_pen
```

如果要批量处理，可以从 `Code/landscape_pen_drawing` 目录执行：

```bash
for img in ../../pics/*.{jpg,jpeg,png,webp}; do
  [ -f "$img" ] || continue
  name=$(basename "$img")
  python main.py --input "$img" --output "outputs/${name%.*}_pen"
done
```

